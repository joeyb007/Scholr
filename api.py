import asyncio
import json
import os
from uuid import uuid4
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from scholr.orchestrator import run_research
from scholr.state import ResearchState

app = FastAPI()

_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*", "X-User-Id"],
)


class ResearchRequest(BaseModel):
    query: str
    session_id: str | None = None
    k: int = 8
    year_from: int | None = None


def _sse(type: str, data) -> str:
    return f"data: {json.dumps({'type': type, 'data': data})}\n\n"


def _build_result(result: ResearchState) -> dict:
    out = result.final_output
    papers = [
        {
            "id": p.paper_id,
            "n": i + 1,
            "title": p.title,
            "authors": p.authors,
            "year": p.year,
            "venue": p.venue,
            "claim": next(
                (c.claim for c in out.evidence_map if p.paper_id in c.paper_ids),
                "",
            ),
        }
        for i, p in enumerate(result.papers)
    ]

    return {
        "session_id": result.session_id,
        "papers_used": out.papers_used,
        "depth_reached": result.depth_reached,
        "answer_paragraphs": out.answer_paragraphs,
        "mechanism": out.mechanism,
        "intuition": out.intuition,
        "limitations": out.limitations,
        "open_questions": out.open_questions,
        "follow_up_questions": out.follow_up_questions,
        "papers": papers,
    }


@app.post("/research")
async def research(body: ResearchRequest):
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    session_id = body.session_id or str(uuid4())

    def on_event(event: str) -> None:
        queue.put_nowait(_sse("progress", event))

    async def run() -> None:
        try:
            result = await run_research(
                query=body.query,
                session_id=session_id,
                on_event=on_event,
                k=body.k,
                year_from=body.year_from,
            )
            if isinstance(result, str):
                queue.put_nowait(_sse("suggestion", result))
            else:
                queue.put_nowait(_sse("result", _build_result(result)))
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
