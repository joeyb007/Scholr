import asyncio
from collections.abc import Callable
from scholr.compression import compress_papers
from scholr.coverage import check_coverage
from scholr.expansion import expand_papers, merge_expansions
from scholr.planner import plan_queries
from scholr.retrieval import retrieve_papers
from scholr.session import fresh_state, load_session, save_session
from scholr.state import EvidenceClaim, ResearchState, existing_ids
from scholr.synthesis import stream_answer, synthesize

MAX_DEPTH = 2
MAX_PAPERS = 15
MAX_RETRIES = 3


async def run_pipeline(
    query: str,
    session_id: str,
    on_event: Callable[[str], None] = lambda _: None,
    on_token: Callable[[str], None] | None = None,
    k: int = 8,
    year_from: int | None = None,
) -> ResearchState:
    state = await load_session(session_id) or fresh_state(query, session_id)
    state.query = query  # always use the current query for planning and synthesis
    on_event("[Session] loading context")

    # Retrieval with retry — planner reformulates on each failed attempt
    failed_queries: list[str] = []
    for attempt in range(MAX_RETRIES + 1):
        if attempt > 0:
            on_event(f"[Planner] no results — reformulating (attempt {attempt}/{MAX_RETRIES})")
        state.planned_queries = await plan_queries(state, on_event, failed_queries or None)
        new_papers = await retrieve_papers(state.planned_queries, existing_ids(state), on_event, k=k, year_from=year_from)
        if new_papers:
            state.papers.extend(new_papers)
            break
        failed_queries = list(state.planned_queries)
    else:
        raise ValueError(
            f"No papers found after {MAX_RETRIES + 1} attempts for: {query!r}. "
            "Try a more specific or differently phrased question."
        )

    for depth in range(MAX_DEPTH):
        on_event(f"[Level {depth}] expanding concepts")
        # Run expansion and coverage concurrently — both only read state.papers
        expansions, coverage = await asyncio.gather(
            expand_papers(state, on_event),
            check_coverage(state, on_event),
        )
        follow_up_queries = merge_expansions(state, expansions)
        if len(state.papers) >= MAX_PAPERS:
            state.depth_reached = depth
            break
        # Combine expansion + coverage gaps into one retrieval round
        extra_queries = list(dict.fromkeys(
            follow_up_queries[:4] + (coverage.extra_queries if not coverage.sufficient else [])
        ))
        if not extra_queries:
            state.depth_reached = depth
            break
        extra = await retrieve_papers(extra_queries[:6], existing_ids(state), on_event, k=k, year_from=year_from)
        state.papers.extend(extra)

    if len(state.papers) > MAX_PAPERS:
        state.papers = state.papers[:MAX_PAPERS]

    on_event("[Compression] extracting key points")
    state.paper_facts = await compress_papers(state, on_event)

    streamed_answer: str | None = None
    if on_token is not None:
        on_event("[Synthesis] streaming answer")
        streamed_answer = await stream_answer(state, on_token)

    state.final_output = await synthesize(state, on_event)

    if streamed_answer is not None:
        state.final_output = state.final_output.model_copy(
            update={"final_answer": streamed_answer}
        )

    _validate_evidence(state)
    await save_session(state)
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
