from collections.abc import Callable
from scholr.llm import llm_parse
from scholr.state import CompressionOutput, Paper, ResearchState

_SYSTEM = """You are a scientific fact extractor. For each provided paper, extract exactly 3 \
atomic factual statements from the abstract. Rules:
- Each statement must be a single, specific, verifiable claim
- Do NOT summarize — extract concrete facts
- Write in present tense, third-person
- Each key_point must be a standalone sentence (not a fragment)"""

_BATCH_SIZE = 4
_ABSTRACT_CHARS = 600


def _format_batch(papers: list[Paper]) -> str:
    return "\n\n".join(
        f"paper_id: {p.paper_id}\ntitle: {p.title}\n"
        f"abstract: {p.abstract[:_ABSTRACT_CHARS]}"
        for p in papers
    )


async def compress_papers(
    state: ResearchState,
    on_event: Callable[[str], None],
) -> dict[str, list[str]]:
    on_event(f"[Compression] extracting facts from {len(state.papers)} papers")
    results: dict[str, list[str]] = {}

    for i in range(0, len(state.papers), _BATCH_SIZE):
        batch = state.papers[i : i + _BATCH_SIZE]
        output = await llm_parse(_SYSTEM, f"Papers to compress:\n\n{_format_batch(batch)}", CompressionOutput)
        for c in output.compressions:
            results[c.paper_id] = c.key_points

    return results
