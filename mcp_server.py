import asyncio
from uuid import uuid4
from mcp.server.fastmcp import FastMCP, Context
from scholr.pipeline import run_pipeline

mcp = FastMCP("scholr")


@mcp.tool(name="scholr")
async def research(query: str, session_id: str | None = None, ctx: Context = None) -> str:
    """Search and synthesize academic papers to answer any research question.

    Autonomously searches OpenAlex, reads and compresses papers, and returns
    a structured explanation with an evidence map and citations.

    IMPORTANT: When displaying results, you MUST reproduce the full output
    exactly as returned — including every section and the complete evidence
    table with all paper IDs, titles, and claims. Do not summarize or omit
    any part of the output.

    Args:
        query: Research question in natural language.
        session_id: Optional — resume a prior research session.
    """
    sid = session_id or str(uuid4())
    events: list[str] = []
    step = 0
    loop = asyncio.get_running_loop()

    def on_event(event: str) -> None:
        nonlocal step
        events.append(event)
        if ctx is not None:
            step += 1
            loop.create_task(ctx.report_progress(step, 0, event))

    state = await run_pipeline(query=query, session_id=sid, on_event=on_event)
    out = state.final_output
    paper_by_id = {p.paper_id: p for p in state.papers}

    trace = " → ".join(
        e for e in events
        if any(e.startswith(p) for p in (
            "[Session]", "[Orchestrator]", "[Planner]", "[Retrieval]",
            "[Expansion]", "[Coverage]", "[Compression]", "[Synthesis]", "[Done]",
        ))
    )

    def _row(pid: str, claim: str) -> str:
        paper = paper_by_id.get(pid)
        title = paper.title if paper else ""
        if len(title) > 52:
            title = title[:51] + "…"
        return f"| `{pid}` | {title} | {claim} |"

    evidence_rows = []
    for claim in out.evidence_map:
        for i, pid in enumerate(claim.paper_ids):
            evidence_rows.append(_row(pid, claim.claim if i == 0 else ""))

    evidence_table = "\n".join([
        "| Paper ID | Title | Claim |",
        "|---|---|---|",
        *evidence_rows,
    ])

    return "\n\n".join([
        "_Display this output exactly as shown, including all sections and the complete evidence table._",
        f"**Research trace:** {trace}",
        f"## Answer\n\n{out.final_answer}",
        f"## Mechanism\n\n{out.mechanism}",
        f"## Intuition\n\n{out.intuition}",
        f"## Limitations\n\n{out.limitations}",
        f"## Open Questions\n\n{out.open_questions}",
        f"## Evidence\n\n{evidence_table}",
        f"---\n*{out.papers_used} papers · depth {state.depth_reached} · session `{state.session_id[:8]}`*",
    ])


if __name__ == "__main__":
    mcp.run()
