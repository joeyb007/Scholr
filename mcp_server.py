from uuid import uuid4
from mcp.server.fastmcp import FastMCP
from scholr.pipeline import run_pipeline

mcp = FastMCP("scholr")


@mcp.tool()
async def research(query: str, session_id: str | None = None) -> dict:
    """Retrieve and synthesize arXiv papers to answer a research question.

    Args:
        query: Natural language research question.
        session_id: Optional session ID to continue a prior conversation.
                    A new session is created if omitted.

    Returns:
        Structured explanation with evidence map, execution trace, and session ID.
    """
    sid = session_id or str(uuid4())
    events: list[str] = []
    state = await run_pipeline(query=query, session_id=sid, on_event=events.append)
    return {
        "session_id": state.session_id,
        "answer": state.final_output.model_dump(),
        "execution_trace": events,
        "papers_used": len(state.papers),
    }


if __name__ == "__main__":
    mcp.run()
