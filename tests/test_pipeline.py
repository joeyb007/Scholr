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


async def test_run_pipeline_raises_on_empty_retrieval():
    with patch("scholr.pipeline.plan_queries", new_callable=AsyncMock, return_value=["q1"]), \
         patch("scholr.pipeline.retrieve_papers", new_callable=AsyncMock, return_value=[]):
        with pytest.raises(ValueError, match="No papers found"):
            await run_pipeline("test query", "s1")


async def test_run_pipeline_saves_session(mocker):
    mock_save = mocker.patch("scholr.pipeline.save_session", new_callable=AsyncMock)
    paper = _make_paper("p1")
    with patch("scholr.pipeline.plan_queries", new_callable=AsyncMock, return_value=["q1"]), \
         patch("scholr.pipeline.retrieve_papers", new_callable=AsyncMock, return_value=[paper]), \
         patch("scholr.pipeline.expand_papers", new_callable=AsyncMock, return_value=ExpansionOutput(expansions=[])), \
         patch("scholr.pipeline.check_coverage", new_callable=AsyncMock, return_value=CoverageOutput(sufficient=True, missing_aspects=[], extra_queries=[])), \
         patch("scholr.pipeline.compress_papers", new_callable=AsyncMock, return_value={"p1": ["fact1"]}), \
         patch("scholr.pipeline.synthesize", new_callable=AsyncMock, return_value=_make_synthesis(["p1"])):
        state = await run_pipeline("test query", "s1")

    mock_save.assert_called_once()
    assert state.session_id == "s1"


async def test_run_pipeline_short_circuits_when_coverage_sufficient(mocker):
    mocker.patch("scholr.pipeline.save_session", new_callable=AsyncMock)
    mock_retrieve = mocker.patch(
        "scholr.pipeline.retrieve_papers", new_callable=AsyncMock, return_value=[_make_paper("p1")]
    )
    # Expansion yields a follow-up query that WOULD drive another retrieval round —
    # only the coverage short-circuit should prevent it.
    expansion = ExpansionOutput(expansions=[
        PaperExpansion(paper_id="p1", concepts=["c"], follow_up_queries=["deeper query"])
    ])
    with patch("scholr.pipeline.plan_queries", new_callable=AsyncMock, return_value=["q1"]), \
         patch("scholr.pipeline.expand_papers", new_callable=AsyncMock, return_value=expansion), \
         patch("scholr.pipeline.check_coverage", new_callable=AsyncMock, return_value=CoverageOutput(sufficient=True, missing_aspects=[], extra_queries=[])), \
         patch("scholr.pipeline.compress_papers", new_callable=AsyncMock, return_value={"p1": ["fact1"]}), \
         patch("scholr.pipeline.synthesize", new_callable=AsyncMock, return_value=_make_synthesis(["p1"])):
        state = await run_pipeline("test query", "s1")

    # Only the initial retrieval ran — the depth loop broke on sufficient coverage.
    mock_retrieve.assert_called_once()
    assert state.depth_reached == 0


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


async def test_run_pipeline_streams_events(mocker):
    mocker.patch("scholr.pipeline.save_session", new_callable=AsyncMock)
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


def _make_many_papers(n: int) -> list:
    return [_make_paper(f"p{i}") for i in range(n)]


async def test_run_pipeline_reranks_when_over_max_papers(mocker):
    mocker.patch("scholr.pipeline.save_session", new_callable=AsyncMock)
    many_papers = _make_many_papers(20)
    reranked = many_papers[:15]
    mock_rerank = mocker.patch("scholr.pipeline.rerank_papers", return_value=reranked)

    with patch("scholr.pipeline.plan_queries", new_callable=AsyncMock, return_value=["q1"]), \
         patch("scholr.pipeline.retrieve_papers", new_callable=AsyncMock, return_value=many_papers), \
         patch("scholr.pipeline.expand_papers", new_callable=AsyncMock, return_value=ExpansionOutput(expansions=[])), \
         patch("scholr.pipeline.check_coverage", new_callable=AsyncMock, return_value=CoverageOutput(sufficient=True, missing_aspects=[], extra_queries=[])), \
         patch("scholr.pipeline.compress_papers", new_callable=AsyncMock, return_value={}), \
         patch("scholr.pipeline.synthesize", new_callable=AsyncMock, return_value=_make_synthesis(["p0"])):
        state = await run_pipeline("test query", "s1")

    mock_rerank.assert_called_once()
    assert len(state.papers) == 15
