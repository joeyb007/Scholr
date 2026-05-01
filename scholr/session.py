from pathlib import Path
from scholr.state import ResearchState

SESSIONS_DIR = Path("sessions")


def load_session(session_id: str) -> ResearchState | None:
    path = SESSIONS_DIR / f"{session_id}.json"
    if not path.exists():
        return None
    try:
        return ResearchState.model_validate_json(path.read_text())
    except Exception:
        return None


def save_session(state: ResearchState) -> None:
    SESSIONS_DIR.mkdir(exist_ok=True)
    path = SESSIONS_DIR / f"{state.session_id}.json"
    path.write_text(state.model_dump_json(indent=2))


def fresh_state(query: str, session_id: str) -> ResearchState:
    return ResearchState(query=query, session_id=session_id)
