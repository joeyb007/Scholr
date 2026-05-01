from collections.abc import Callable
from scholr.llm import llm_parse
from scholr.state import ResearchState, SynthesisResult

_SYSTEM = """You are a scientific synthesis engine. Produce a structured explanation grounded \
entirely in the provided paper facts. Rules:
- Every claim in evidence_map MUST cite at least one paper_id from the provided list
- Do NOT make any claim that is not supported by a paper_id in the list
- papers_used must equal the number of distinct paper_ids cited across all evidence_map entries
- depth_reached must be set to the value provided in the context"""


async def synthesize(
    state: ResearchState,
    on_event: Callable[[str], None],
) -> SynthesisResult:
    on_event("[Synthesis] generating final explanation")

    facts_text = "\n\n".join(
        f"paper_id: {pid}\nfacts:\n" + "\n".join(f"  - {f}" for f in facts)
        for pid, facts in state.paper_facts.items()
    )
    concept_text = "\n".join(
        f"  {concept}: {', '.join(pids)}"
        for concept, pids in state.concept_to_papers.items()
    )
    valid_ids = [p.paper_id for p in state.papers]

    user = (
        f"Question: {state.query}\n\n"
        f"Paper facts:\n{facts_text}\n\n"
        f"Concept map:\n{concept_text}\n\n"
        f"Valid paper IDs (only cite these): {valid_ids}\n"
        f"depth_reached: {state.depth_reached}"
    )
    result = await llm_parse(_SYSTEM, user, SynthesisResult)
    on_event(f"[Synthesis] generated {len(result.evidence_map)} evidence claims")
    return result
