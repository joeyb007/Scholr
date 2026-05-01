import pytest
from unittest.mock import AsyncMock, patch
from scholr.pipeline import run_pipeline, _validate_evidence
from scholr.state import (
    EvidenceClaim, ExpansionOutput, PaperExpansion,
    ResearchState, Paper, SynthesisResult, CoverageOutput,
)


def _make_paper(pid: str) -> Paper:
    return Paper(paper_id=pid, title=f"T{pid}", abstract=f"A{pid}", source_query="q")


def _make_synthesis(paper_ids: list[str]) -> SynthesisResult:
    return SynthesisResult(
        final_answer="answer", key_concepts=["c1"],
        intuition="i", mechanism="m", limitations="l", open_questions="o",
        evidence_map=[EvidenceClaim(claim="claim", paper_ids=paper_ids)],
        papers_used=len(paper_ids), depth_reached=0,
    )


async def test_run_pipeline_raises_on_empty_retrieval(tmp_path, monkeypatch):
    monkeypatch.setattr("scholr.session.SESSIONS_DIR", tmp_path)

    with patch("scholr.pipeline.plan_queries", new_callable=AsyncMock, return_value=["q1"]), \
         patch("scholr.pipeline.retrieve_papers", new_callable=AsyncMock, return_value=[]):
        with pytest.raises(ValueError, match="No papers retrieved"):
            await run_pipeline("test query", "s1")


async def test_run_pipeline_saves_session(tmp_path, monkeypatch):
    monkeypatch.setattr("scholr.session.SESSIONS_DIR", tmp_path)

    paper = _make_paper("p1")
    with patch("scholr.pipeline.plan_queries", new_callable=AsyncMock, return_value=["q1"]), \
         patch("scholr.pipeline.retrieve_papers", new_callable=AsyncMock, return_value=[paper]), \
         patch("scholr.pipeline.expand_papers", new_callable=AsyncMock, return_value=ExpansionOutput(expansions=[])), \
         patch("scholr.pipeline.check_coverage", new_callable=AsyncMock, return_value=CoverageOutput(sufficient=True, missing_aspects=[], extra_queries=[])), \
         patch("scholr.pipeline.compress_papers", new_callable=AsyncMock, return_value={"p1": ["fact1"]}), \
         patch("scholr.pipeline.synthesize", new_callable=AsyncMock, return_value=_make_synthesis(["p1"])):
        state = await run_pipeline("test query", "s1")

    assert (tmp_path / "s1.json").exists()
    assert state.session_id == "s1"


def test_validate_evidence_strips_hallucinated_ids(sample_synthesis, sample_paper):
    state = ResearchState(
        query="test", session_id="s1",
        papers=[sample_paper],
        final_output=SynthesisResult(
            final_answer="answer", key_concepts=[], intuition="", mechanism="",
            limitations="", open_questions="",
            evidence_map=[
                EvidenceClaim(
                    claim="real claim",
                    paper_ids=[sample_paper.paper_id, "http://arxiv.org/abs/FAKE"],
                )
            ],
            papers_used=1, depth_reached=0,
        ),
    )
    _validate_evidence(state)
    assert state.final_output.evidence_map[0].paper_ids == [sample_paper.paper_id]


def test_validate_evidence_keeps_valid_ids(sample_paper, sample_synthesis):
    state = ResearchState(
        query="test", session_id="s1",
        papers=[sample_paper],
        final_output=sample_synthesis,
    )
    _validate_evidence(state)
    assert sample_paper.paper_id in state.final_output.evidence_map[0].paper_ids


async def test_run_pipeline_streams_events(tmp_path, monkeypatch):
    monkeypatch.setattr("scholr.session.SESSIONS_DIR", tmp_path)

    paper = _make_paper("p1")
    with patch("scholr.pipeline.plan_queries", new_callable=AsyncMock, return_value=["q1"]), \
         patch("scholr.pipeline.retrieve_papers", new_callable=AsyncMock, return_value=[paper]), \
         patch("scholr.pipeline.expand_papers", new_callable=AsyncMock, return_value=ExpansionOutput(expansions=[])), \
         patch("scholr.pipeline.check_coverage", new_callable=AsyncMock, return_value=CoverageOutput(sufficient=True, missing_aspects=[], extra_queries=[])), \
         patch("scholr.pipeline.compress_papers", new_callable=AsyncMock, return_value={"p1": ["fact1"]}), \
         patch("scholr.pipeline.synthesize", new_callable=AsyncMock, return_value=_make_synthesis(["p1"])):
        events = []
        await run_pipeline("test query", "s1", on_event=events.append)

    assert any("[Done]" in e for e in events)
    assert any("[Session]" in e for e in events)
