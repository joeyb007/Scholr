import asyncio
from collections.abc import Callable
from scholr.llm import llm_parse
from scholr.reranking import select_top_by_similarity
from scholr.state import ExpansionOutput, Paper, ResearchState

# Follow-up queries come from within a paper's content, not from breadth across papers.
# Expanding the 5 most relevant new papers yields ~15 candidate sub-questions; the pipeline
# only uses the top 4, so this is ample supply while keeping expansion output small.
EXPAND_TOP_N = 5

_SYSTEM = """You are a research concept extractor. For each provided paper, extract up to 3 \
specific technical concepts and suggest up to 3 follow-up arXiv keyword search queries that \
would deepen understanding of the topic. Rules:
- Concepts must be specific technical terms (e.g. "self-attention", not "neural networks")
- Follow-up queries must be keyword-based, not conversational
- Limit follow_up_queries to 3 per paper maximum
- Limit concepts to 3 per paper maximum"""


async def expand_papers(
    state: ResearchState,
    candidates: list[Paper],
    on_event: Callable[[str], None],
) -> ExpansionOutput:
    """Expands only the most relevant papers from the given candidate batch (the
    papers just retrieved), not the full accumulated pool. Narrowing by bi-encoder
    relevance keeps follow-up queries on-topic and caps expansion output cost."""
    # Bi-encoder inference is synchronous and CPU-bound — offload it so it doesn't block
    # the event loop (and starve concurrent threads' I/O) while it runs on Railway's CPU.
    focused = await asyncio.to_thread(select_top_by_similarity, state.query, candidates, EXPAND_TOP_N)
    on_event(f"[Expansion] processing {len(focused)} of {len(candidates)} new papers")
    if not focused:
        return ExpansionOutput(expansions=[])
    papers_text = "\n\n".join(
        f"paper_id: {p.paper_id}\ntitle: {p.title}\nabstract: {p.abstract[:600]}"
        for p in focused
    )
    user = f"Papers to expand:\n\n{papers_text}"
    return await llm_parse(_SYSTEM, user, ExpansionOutput)


def merge_expansions(
    state: ResearchState,
    output: ExpansionOutput,
) -> list[str]:
    follow_up_queries: list[str] = []
    seen_queries: set[str] = set()

    for expansion in output.expansions:
        for concept in expansion.concepts:
            if concept not in state.concept_to_papers:
                state.concept_to_papers[concept] = []
            if expansion.paper_id not in state.concept_to_papers[concept]:
                state.concept_to_papers[concept].append(expansion.paper_id)

        for query in expansion.follow_up_queries:
            if query not in seen_queries:
                seen_queries.add(query)
                follow_up_queries.append(query)

    return follow_up_queries
