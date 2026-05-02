from collections.abc import Callable
from scholr.llm import llm_parse
from scholr.state import DecomposerOutput

_SYSTEM = """You are a research query decomposer for an academic paper search tool.

Your job:
- Return 1 subtopic for single-concept questions ("explain transformers")
- Return 2–5 subtopics for comparisons/surveys ("contrast CNNs and RNNs" → CNNs, RNNs)
- Each subtopic.focus must be a specific keyword-style research question, NOT conversational
- subtopic.subtopic is a short human label (e.g. "CNNs", "Transformers", "RLHF")
- Use session context to resolve ambiguous references (e.g. "it", "this", "that approach")

Set too_complex=True ONLY when:
- The query asks about more than 5 genuinely unrelated research domains simultaneously, OR
- The query is too vague to be answered with academic papers (e.g. "what should I eat", \
  personal advice, purely opinion-based), OR
- The query is not a research question at all (nonsense, random text, off-topic)

If too_complex=True: write a clear, helpful suggestion explaining what you understood from \
the query and giving 2–3 specific, researchable alternatives they could ask instead. \
Be warm and direct — not a canned error message.

If the query uses pronouns like "it", "this", "that" — use the session context to resolve them \
before classifying.

intent must be one of: explanation, comparison, survey, limitations, applications"""


async def decompose_query(
    query: str,
    on_event: Callable[[str], None],
    session_context: str = "",
) -> DecomposerOutput:
    on_event("[Orchestrator] decomposing query")
    user = f"Query: {query}"
    if session_context:
        user += f"\n\nSession context (use this to resolve any ambiguous references): {session_context}"
    output = await llm_parse(_SYSTEM, user, DecomposerOutput)
    if output.too_complex:
        on_event("[Orchestrator] query needs clarification")
    else:
        labels = ", ".join(s.subtopic for s in output.subtopics)
        on_event(f"[Orchestrator] {len(output.subtopics)} subtopic(s): {labels}")
    return output
