from collections.abc import Callable
from scholr.llm import llm_parse
from scholr.state import ExpansionOutput, ResearchState

_SYSTEM = """You are a research concept extractor. For each provided paper, extract up to 3 \
specific technical concepts and suggest up to 3 follow-up arXiv keyword search queries that \
would deepen understanding of the topic. Rules:
- Concepts must be specific technical terms (e.g. "self-attention", not "neural networks")
- Follow-up queries must be keyword-based, not conversational
- Limit follow_up_queries to 3 per paper maximum
- Limit concepts to 3 per paper maximum"""


async def expand_papers(
    state: ResearchState,
    on_event: Callable[[str], None],
) -> ExpansionOutput:
    on_event(f"[Expansion] processing {len(state.papers)} papers")
    papers_text = "\n\n".join(
        f"paper_id: {p.paper_id}\ntitle: {p.title}\nabstract: {p.abstract}"
        for p in state.papers
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
