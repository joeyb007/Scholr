import asyncio
import json
import logging
import os
import re
import traceback
from uuid import uuid4
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from scholr.orchestrator import run_research
from scholr.state import ResearchState

app = FastAPI()

_IP_LIMIT = 60        # max requests per IP per day
_ip_counts: dict[str, list] = {}  # {ip: [count, date_str]}

def _check_ip(ip: str) -> bool:
    from datetime import date
    today = str(date.today())
    entry = _ip_counts.get(ip)
    if not entry or entry[1] != today:
        _ip_counts[ip] = [1, today]
        return True
    if entry[0] >= _IP_LIMIT:
        return False
    entry[0] += 1
    return True

@app.on_event("startup")
async def startup():
    """Warm expensive one-time costs before the first user query lands:
    the OpenAI TLS/connection pool and both reranker models. Each is guarded
    so a warmup failure never blocks the server from accepting traffic."""
    import time

    from scholr.llm import get_client
    from scholr.reranking import _get_bi_encoder, _get_cross_encoder

    # OpenAI connection pool — a cheap GET establishes TLS + keep-alive socket.
    t0 = time.perf_counter()
    try:
        await get_client().models.list()
        logger.info("Warmup: OpenAI connection ready (%.0fms)", (time.perf_counter() - t0) * 1000)
    except Exception as e:
        logger.warning("Warmup: OpenAI connection failed (%s) — first query pays the cost", e)

    # Reranker models — load weights into memory off the event loop.
    t0 = time.perf_counter()
    try:
        await asyncio.gather(
            asyncio.to_thread(_get_bi_encoder),
            asyncio.to_thread(_get_cross_encoder),
        )
        logger.info("Warmup: reranker models loaded (%.0fms)", (time.perf_counter() - t0) * 1000)
    except Exception as e:
        logger.warning("Warmup: reranker model load failed (%s) — first rerank pays the cost", e)

    logger.info("Scholr API started")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
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
async def research(body: ResearchRequest, request: Request):
    ip = request.headers.get("X-Forwarded-For", request.client.host).split(",")[0].strip()
    if not _check_ip(ip):
        raise HTTPException(status_code=429, detail="Too many requests — try again tomorrow")
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    session_id = body.session_id or str(uuid4())

    logger.info("Query received: %r (session=%s, k=%d, year_from=%s)", body.query, session_id, body.k, body.year_from)

    def on_event(event: str) -> None:
        # Paper markers (optionally prefixed with a subtopic, e.g. "[CNNs] [Paper]\t…")
        # become structured `paper` events so the UI can stream sources in live.
        marker = "[Paper]\t"
        idx = event.find(marker)
        if idx != -1:
            angle_m = re.match(r"^\s*\[([^\]]+)\]", event[:idx])
            parts = event[idx + len(marker):].split("\t")
            queue.put_nowait(_sse("paper", {
                "id": parts[0] if len(parts) > 0 else "",
                "angle": angle_m.group(1) if angle_m else "",
                "title": parts[1] if len(parts) > 1 else "",
                "authors": parts[2] if len(parts) > 2 else "",
                "year": parts[3] if len(parts) > 3 else "",
                "abstract": parts[4] if len(parts) > 4 else "",
            }))
            return
        logger.info(event)
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
            logger.error("Pipeline error for query %r:\n%s", body.query, traceback.format_exc())
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
