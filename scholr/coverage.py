from collections.abc import Callable
from scholr.llm import llm_parse
from scholr.state import CoverageOutput, ResearchState

_SYSTEM = """You are a research coverage evaluator. Given a question and retrieved papers, \
determine if the collection is sufficient to answer the question comprehensively. Coverage \
is sufficient if the papers collectively address: the core mechanism, at least one limitation, \
and the theoretical basis. If coverage is insufficient, identify specific missing aspects and \
provide targeted arXiv keyword search queries to fill the gaps."""


async def check_coverage(
    state: ResearchState,
    on_event: Callable[[str], None],
) -> CoverageOutput:
    on_event(f"[Coverage] evaluating {len(state.papers)} papers")
    papers_text = "\n".join(
        f"- {p.title} (id: {p.paper_id})" for p in state.papers
    )
    user = (
        f"Question: {state.query}\n\n"
        f"Retrieved papers:\n{papers_text}"
    )
    result = await llm_parse(_SYSTEM, user, CoverageOutput)
    on_event(f"[Coverage] sufficient={result.sufficient}")
    return result
