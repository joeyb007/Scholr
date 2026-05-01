from collections.abc import Callable
from scholr.compression import compress_papers
from scholr.coverage import check_coverage
from scholr.expansion import expand_papers, merge_expansions
from scholr.planner import plan_queries
from scholr.retrieval import retrieve_papers
from scholr.session import fresh_state, load_session, save_session
from scholr.state import EvidenceClaim, ResearchState, existing_ids
from scholr.synthesis import synthesize

MAX_DEPTH = 2
MAX_PAPERS = 12


async def run_pipeline(
    query: str,
    session_id: str,
    on_event: Callable[[str], None] = lambda _: None,
) -> ResearchState:
    state = load_session(session_id) or fresh_state(query, session_id)
    on_event("[Session] loading context")

    state.planned_queries = await plan_queries(state, on_event)
    new_papers = await retrieve_papers(state.planned_queries, existing_ids(state), on_event)
    state.papers.extend(new_papers)

    if not state.papers:
        raise ValueError(f"No papers retrieved for query: {query!r}. Try rephrasing.")

    for depth in range(MAX_DEPTH):
        on_event(f"[Level {depth}] expanding concepts")
        expansions = await expand_papers(state, on_event)
        follow_up_queries = merge_expansions(state, expansions)
        if len(state.papers) >= MAX_PAPERS or not follow_up_queries:
            state.depth_reached = depth
            break
        extra = await retrieve_papers(follow_up_queries[:8], existing_ids(state), on_event)
        state.papers.extend(extra)

    on_event("[Coverage] checking completeness")
    coverage = await check_coverage(state, on_event)
    if not coverage.sufficient:
        on_event("[Coverage] retrieving missing aspects")
        extra = await retrieve_papers(coverage.extra_queries, existing_ids(state), on_event)
        state.papers.extend(extra)

    on_event("[Compression] extracting key points")
    state.paper_facts = await compress_papers(state, on_event)

    on_event("[Synthesis] generating final explanation")
    state.final_output = await synthesize(state, on_event)
    _validate_evidence(state)

    save_session(state)
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
