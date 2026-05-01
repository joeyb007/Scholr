from collections.abc import Callable
from scholr.llm import llm_parse
from scholr.state import CompressionOutput, ResearchState

_SYSTEM = """You are a scientific fact extractor. For each provided paper, extract exactly 3 \
atomic factual statements from the abstract. Rules:
- Each statement must be a single, specific, verifiable claim
- Do NOT summarize — extract concrete facts
- Write in present tense, third-person
- Each key_point must be a standalone sentence (not a fragment)"""


async def compress_papers(
    state: ResearchState,
    on_event: Callable[[str], None],
) -> dict[str, list[str]]:
    on_event(f"[Compression] extracting facts from {len(state.papers)} papers")
    papers_text = "\n\n".join(
        f"paper_id: {p.paper_id}\ntitle: {p.title}\nabstract: {p.abstract}"
        for p in state.papers
    )
    user = f"Papers to compress:\n\n{papers_text}"
    output = await llm_parse(_SYSTEM, user, CompressionOutput)
    return {c.paper_id: c.key_points for c in output.compressions}
