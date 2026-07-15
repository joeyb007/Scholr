import asyncio
import time
from collections.abc import Callable
from scholr.compression import compress_papers
from scholr.coverage import check_coverage
from scholr.expansion import expand_papers, merge_expansions
from scholr.planner import plan_queries
from scholr.reranking import rerank_papers
from scholr.retrieval import retrieve_papers
from scholr.session import fresh_state, load_session, save_session
from scholr.state import EvidenceClaim, Paper, ResearchState, existing_ids
from scholr.synthesis import stream_answer, synthesize

MAX_DEPTH = 2
MAX_CANDIDATES = 60   # candidate pool size before reranking narrows it down
MAX_PAPERS = 15       # final paper count fed to synthesis, after reranking
BI_ENCODER_TOP_N = 25 # bi-encoder narrows candidates to this before the cross-encoder
MAX_RETRIES = 3


async def _timed(label: str, coro, on_event: Callable[[str], None]):
    t0 = time.perf_counter()
    result = await coro
    ms = (time.perf_counter() - t0) * 1000
    on_event(f"[Timing] {label}: {ms:.0f}ms")
    return result


async def _gather_candidates(
    query: str,
    session_id: str,
    on_event: Callable[[str], None],
    k: int = 8,
    year_from: int | None = None,
) -> ResearchState:
    """Runs planning, retrieval, and the expansion/coverage loop. Returns a
    state with up to MAX_CANDIDATES papers — no final truncation or reranking
    applied. Shared by run_pipeline() and the offline eval harness."""
    state = await _timed("load_session", load_session(session_id), on_event) or fresh_state(query, session_id)
    state.query = query
    on_event("[Session] loading context")

    failed_queries: list[str] = []
    last_batch: list[Paper] = []  # most recently retrieved papers — the set expansion mines
    for attempt in range(MAX_RETRIES + 1):
        if attempt > 0:
            on_event(f"[Planner] no results — reformulating (attempt {attempt}/{MAX_RETRIES})")
        state.planned_queries = await _timed("plan_queries", plan_queries(state, on_event, failed_queries or None), on_event)
        new_papers = await _timed(
            f"retrieve_papers (initial, {len(state.planned_queries)} queries)",
            retrieve_papers(state.planned_queries, existing_ids(state), on_event, k=k, year_from=year_from),
            on_event,
        )
        if new_papers:
            state.papers.extend(new_papers)
            last_batch = new_papers
            on_event(f"[Retrieval] {len(new_papers)} papers found, {len(state.papers)} total")
            break
        failed_queries = list(state.planned_queries)
    else:
        raise ValueError(
            f"No papers found after {MAX_RETRIES + 1} attempts for: {query!r}. "
            "Try a more specific or differently phrased question."
        )

    for depth in range(MAX_DEPTH):
        on_event(f"[Level {depth}] expanding concepts")
        # Expansion mines only the newly-retrieved batch; coverage judges the full pool.
        # Both run concurrently and only read state.
        t0 = time.perf_counter()
        expansions, coverage = await asyncio.gather(
            expand_papers(state, last_batch, on_event),
            check_coverage(state, on_event),
        )
        ms = (time.perf_counter() - t0) * 1000
        on_event(f"[Timing] expand+coverage (depth {depth}, concurrent): {ms:.0f}ms")
        on_event(f"[Coverage] sufficient={coverage.sufficient}, gap_queries={len(coverage.extra_queries)}")

        follow_up_queries = merge_expansions(state, expansions)
        if len(state.papers) >= MAX_CANDIDATES:
            state.depth_reached = depth
            break
        # Coverage already ran concurrently above — honor its stop signal instead of
        # recursing further on expansion's follow-ups when the pool already covers the topic.
        if coverage.sufficient:
            state.depth_reached = depth
            break
        extra_queries = list(dict.fromkeys(
            follow_up_queries[:4] + coverage.extra_queries
        ))
        if not extra_queries:
            state.depth_reached = depth
            break
        extra = await _timed(
            f"retrieve_papers (depth {depth}, {len(extra_queries[:6])} queries)",
            retrieve_papers(extra_queries[:6], existing_ids(state), on_event, k=k, year_from=year_from),
            on_event,
        )
        state.papers.extend(extra)
        last_batch = extra
        on_event(f"[Retrieval] {len(extra)} new papers, {len(state.papers)} total")

    return state


async def run_pipeline(
    query: str,
    session_id: str,
    on_event: Callable[[str], None] = lambda _: None,
    on_token: Callable[[str], None] | None = None,
    k: int = 8,
    year_from: int | None = None,
) -> ResearchState:
    t_pipeline = time.perf_counter()

    state = await _gather_candidates(query, session_id, on_event, k=k, year_from=year_from)

    if len(state.papers) > MAX_PAPERS:
        on_event(f"[Rerank] narrowing {len(state.papers)} candidates to {MAX_PAPERS}")
        t0 = time.perf_counter()
        state.papers = rerank_papers(state.query, state.papers, BI_ENCODER_TOP_N, MAX_PAPERS)
        on_event(f"[Timing] rerank: {(time.perf_counter() - t0) * 1000:.0f}ms")

    on_event(f"[Compression] extracting key points from {len(state.papers)} papers")
    state.paper_facts = await _timed("compress_papers", compress_papers(state, on_event), on_event)

    streamed_answer: str | None = None
    if on_token is not None:
        on_event("[Synthesis] streaming answer")
        streamed_answer = await _timed("stream_answer", stream_answer(state, on_token), on_event)

    state.final_output = await _timed("synthesize", synthesize(state, on_event), on_event)

    if streamed_answer is not None:
        state.final_output = state.final_output.model_copy(
            update={"final_answer": streamed_answer}
        )

    _validate_evidence(state)
    await _timed("save_session", save_session(state), on_event)

    total_ms = (time.perf_counter() - t_pipeline) * 1000
    on_event(f"[Timing] TOTAL pipeline: {total_ms:.0f}ms")
    on_event("[Done]")
    return state


def _validate_evidence(state: ResearchState) -> None:
    valid_ids = existing_ids(state)
    validated_claims = [
        EvidenceClaim(
            claim=claim.claim,
            paper_ids=[pid for pid in claim.paper_ids if pid in valid_ids],
        )
        for claim in state.final_output.evidence_map
        if any(pid in valid_ids for pid in claim.paper_ids)
    ]
    state.final_output = state.final_output.model_copy(
        update={"evidence_map": validated_claims}
    )
