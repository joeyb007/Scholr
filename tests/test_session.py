import json
import pytest
from pathlib import Path
from scholr.session import load_session, save_session, fresh_state
from scholr.state import ResearchState


def test_fresh_state():
    state = fresh_state("explain transformers", "session-1")
    assert state.query == "explain transformers"
    assert state.session_id == "session-1"
    assert state.papers == []


def test_save_and_load_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr("scholr.session.SESSIONS_DIR", tmp_path)
    state = fresh_state("explain transformers", "session-1")
    state.planned_queries = ["transformer attention mechanism"]

    save_session(state)

    loaded = load_session("session-1")
    assert loaded is not None
    assert loaded.query == "explain transformers"
    assert loaded.planned_queries == ["transformer attention mechanism"]


def test_load_session_returns_none_for_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("scholr.session.SESSIONS_DIR", tmp_path)
    result = load_session("nonexistent-session")
    assert result is None


def test_load_session_returns_none_on_schema_drift(tmp_path, monkeypatch):
    monkeypatch.setattr("scholr.session.SESSIONS_DIR", tmp_path)
    path = tmp_path / "bad-session.json"
    path.write_text(json.dumps({"completely": "wrong", "schema": True}))

    result = load_session("bad-session")
    assert result is None


def test_save_creates_sessions_dir(tmp_path, monkeypatch):
    sessions_dir = tmp_path / "new_sessions"
    monkeypatch.setattr("scholr.session.SESSIONS_DIR", sessions_dir)
    state = fresh_state("query", "s1")
    save_session(state)
    assert sessions_dir.exists()
    assert (sessions_dir / "s1.json").exists()
