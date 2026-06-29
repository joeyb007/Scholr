from scholr.session import load_session, save_session, fresh_state


def test_fresh_state():
    state = fresh_state("explain transformers", "session-1")
    assert state.query == "explain transformers"
    assert state.session_id == "session-1"
    assert state.papers == []


async def test_load_session_returns_none_without_database_url(monkeypatch):
    monkeypatch.setattr("scholr.session._DB_URL", None)
    result = await load_session("session-1")
    assert result is None


async def test_save_session_noops_without_database_url(monkeypatch, mocker):
    monkeypatch.setattr("scholr.session._DB_URL", None)
    mock_to_thread = mocker.patch("asyncio.to_thread")
    await save_session(fresh_state("query", "s1"))
    mock_to_thread.assert_not_called()


async def test_save_and_load_round_trip(monkeypatch, mocker):
    monkeypatch.setattr("scholr.session._DB_URL", "postgres://fake")
    state = fresh_state("explain transformers", "session-1")
    state.planned_queries = ["transformer attention mechanism"]

    stored: dict[str, str] = {}

    def fake_sync_save(session_id: str, state_json: str) -> None:
        stored[session_id] = state_json

    def fake_sync_load(session_id: str) -> str | None:
        return stored.get(session_id)

    mocker.patch("scholr.session._sync_save", side_effect=fake_sync_save)
    mocker.patch("scholr.session._sync_load", side_effect=fake_sync_load)

    await save_session(state)
    loaded = await load_session("session-1")

    assert loaded is not None
    assert loaded.query == "explain transformers"
    assert loaded.planned_queries == ["transformer attention mechanism"]


async def test_load_session_returns_none_for_missing(monkeypatch, mocker):
    monkeypatch.setattr("scholr.session._DB_URL", "postgres://fake")
    mocker.patch("scholr.session._sync_load", return_value=None)

    result = await load_session("nonexistent-session")
    assert result is None


async def test_load_session_returns_none_on_schema_drift(monkeypatch, mocker):
    monkeypatch.setattr("scholr.session._DB_URL", "postgres://fake")
    mocker.patch("scholr.session._sync_load", return_value='{"completely": "wrong", "schema": true}')

    result = await load_session("bad-session")
    assert result is None


async def test_load_session_returns_none_on_db_error(monkeypatch, mocker):
    monkeypatch.setattr("scholr.session._DB_URL", "postgres://fake")
    mocker.patch("scholr.session._sync_load", side_effect=Exception("connection refused"))

    result = await load_session("session-1")
    assert result is None


async def test_save_session_swallows_db_error(monkeypatch, mocker):
    monkeypatch.setattr("scholr.session._DB_URL", "postgres://fake")
    mocker.patch("scholr.session._sync_save", side_effect=Exception("connection refused"))

    # Should not raise even though the underlying save fails.
    await save_session(fresh_state("query", "s1"))
