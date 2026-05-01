from collections.abc import Callable
from scholr.llm import llm_parse
from scholr.state import DecomposerOutput

_SYSTEM = """You are a research query decomposer. Analyze the user's question and break it \
into focused subtopics for parallel research.

Rules:
- Return 1 subtopic for single-concept questions ("explain transformers")
- Return 2–5 subtopics for comparisons, surveys, or multi-concept questions
  ("contrast CNNs and RNNs" → subtopics: CNNs, RNNs)
  ("compare major sequence models" → subtopics: RNNs, CNNs, Transformers, SSMs)
- Each subtopic.focus must be a specific arXiv-style keyword question, NOT conversational
- subtopic.subtopic is a short human label (e.g. "CNNs", "Transformers", "RLHF")
- Set too_complex=True ONLY if the query spans more than 5 fundamentally unrelated research \
  domains that cannot be meaningfully synthesised together
- If too_complex=True: leave subtopics empty and populate suggestion with 2–3 concrete, \
  simpler alternative questions the user could ask instead
- intent must be one of: explanation, comparison, survey, limitations, applications"""


async def decompose_query(
    query: str,
    on_event: Callable[[str], None],
) -> DecomposerOutput:
    on_event("[Orchestrator] decomposing query")
    output = await llm_parse(
        _SYSTEM,
        f"Query: {query}",
        DecomposerOutput,
    )
    if output.too_complex:
        on_event("[Orchestrator] query too complex")
    else:
        labels = ", ".join(s.subtopic for s in output.subtopics)
        on_event(f"[Orchestrator] {len(output.subtopics)} subtopic(s): {labels}")
    return output
