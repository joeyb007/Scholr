"""
End-to-end integration tests. Hits real arXiv and OpenAI APIs.
Run with: pytest tests/test_e2e.py -v -m e2e
Requires: OPENAI_API_KEY set in environment.
"""
import pytest
from scholr.pipeline import run_pipeline
from scholr.state import ResearchState


@pytest.mark.e2e
async def test_full_pipeline_transformer_query(tmp_path, monkeypatch):
    monkeypatch.setattr("scholr.session.SESSIONS_DIR", tmp_path)

    state = await run_pipeline(
        query="explain transformer self-attention mechanism",
        session_id="e2e-test-001",
    )

    assert isinstance(state, ResearchState)
    assert len(state.papers) > 0
    assert state.final_output is not None
    assert state.final_output.final_answer != ""
    assert len(state.final_output.evidence_map) > 0

    for claim in state.final_output.evidence_map:
        valid_ids = {p.paper_id for p in state.papers}
        assert all(pid in valid_ids for pid in claim.paper_ids), \
            f"Hallucinated paper_id found in claim: {claim.claim}"


@pytest.mark.e2e
async def test_session_follow_up(tmp_path, monkeypatch):
    monkeypatch.setattr("scholr.session.SESSIONS_DIR", tmp_path)

    state1 = await run_pipeline(
        query="explain transformer attention",
        session_id="e2e-followup",
    )
    assert len(state1.concept_to_papers) > 0

    state2 = await run_pipeline(
        query="what are the limitations of this approach",
        session_id="e2e-followup",
    )
    assert state2.final_output is not None
