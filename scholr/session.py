import asyncio
import os

from scholr.state import ResearchState

_DB_URL = os.environ.get("DATABASE_URL")


def _sync_load(session_id: str) -> str | None:
    import psycopg2
    conn = psycopg2.connect(_DB_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT state FROM research_sessions WHERE session_id = %s", (session_id,))
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


def _sync_save(session_id: str, state_json: str) -> None:
    import psycopg2
    conn = psycopg2.connect(_DB_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO research_sessions (session_id, state, updated_at)
                   VALUES (%s, %s, NOW())
                   ON CONFLICT (session_id) DO UPDATE SET state = %s, updated_at = NOW()""",
                (session_id, state_json, state_json),
            )
        conn.commit()
    finally:
        conn.close()


async def load_session(session_id: str) -> ResearchState | None:
    if not _DB_URL:
        return None
    try:
        raw = await asyncio.to_thread(_sync_load, session_id)
        if raw:
            return ResearchState.model_validate_json(raw)
    except Exception:
        pass
    return None


async def save_session(state: ResearchState) -> None:
    if not _DB_URL:
        return
    try:
        await asyncio.to_thread(_sync_save, state.session_id, state.model_dump_json())
    except Exception:
        pass


def fresh_state(query: str, session_id: str) -> ResearchState:
    return ResearchState(query=query, session_id=session_id)
