import asyncio
import json
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from scholr.orchestrator import run_research
from scholr.state import ResearchState

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


class ResearchRequest(BaseModel):
    query: str
    session_id: str | None = None


def _sse(type: str, data) -> str:
    return f"data: {json.dumps({'type': type, 'data': data})}\n\n"


@app.post("/research")
async def research(body: ResearchRequest):
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    session_id = body.session_id or str(uuid4())

    def on_event(event: str) -> None:
        queue.put_nowait(_sse("progress", event))

    def on_token(token: str) -> None:
        queue.put_nowait(_sse("token", token))

    async def run() -> None:
        try:
            result = await run_research(
                query=body.query,
                session_id=session_id,
                on_event=on_event,
                on_token=on_token,
            )
            if isinstance(result, str):
                queue.put_nowait(_sse("error", result))
            else:
                out = result.final_output
                paper_by_id = {p.paper_id: p for p in result.papers}
                evidence = [
                    {
                        "claim": claim.claim,
                        "papers": [
                            {"id": pid, "title": paper_by_id[pid].title if pid in paper_by_id else pid}
                            for pid in claim.paper_ids
                        ],
                    }
                    for claim in out.evidence_map
                ]
                queue.put_nowait(_sse("result", {
                    "session_id": result.session_id,
                    "papers_used": out.papers_used,
                    "depth_reached": result.depth_reached,
                    "mechanism": out.mechanism,
                    "intuition": out.intuition,
                    "limitations": out.limitations,
                    "open_questions": out.open_questions,
                    "evidence": evidence,
                }))
        except Exception as e:
            queue.put_nowait(_sse("error", str(e)))
        finally:
            queue.put_nowait(None)

    async def generate():
        task = asyncio.create_task(run())
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
        await task

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
