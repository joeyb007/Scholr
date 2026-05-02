import pytest
from unittest.mock import AsyncMock, patch
from scholr.orchestrator import run_research, _merge_states
from scholr.state import (
    DecomposerOutput, SubtopicQuery, ResearchState,
    Paper, SynthesisResult, EvidenceClaim,
)


def _make_paper(pid: str) -> Paper:
    return Paper(paper_id=pid, title=f"T{pid}", abstract=f"A{pid}", source_query="q")


def _make_state(session_id: str, *paper_ids: str) -> ResearchState:
    state = ResearchState(query="test", session_id=session_id)
    state.papers = [_make_paper(pid) for pid in paper_ids]
    state.paper_facts = {pid: ["fact"] for pid in paper_ids}
    state.concept_to_papers = {"concept": list(paper_ids)}
    state.final_output = SynthesisResult(
        final_answer="answer", key_concepts=["c"],
        intuition="i", mechanism="m", limitations="l", open_questions="o",
        evidence_map=[EvidenceClaim(claim="claim", paper_ids=[paper_ids[0]])],
        papers_used=len(paper_ids), depth_reached=0,
    )
    return state


async def test_run_research_too_complex_returns_suggestion(mocker, tmp_path):
    decomp = DecomposerOutput(
        subtopics=[], too_complex=True,
        suggestion="Try asking about CNNs and RNNs separately.",
        intent="survey", is_followup=False,
    )
    mocker.patch("scholr.orchestrator.decompose_query", new_callable=AsyncMock, return_value=decomp)
    mocker.patch("scholr.session.SESSIONS_DIR", tmp_path)

    result = await run_research("explain everything in AI", "s1")
    assert isinstance(result, str)
    assert "CNNs" in result


async def test_run_research_single_subtopic_calls_pipeline(mocker, tmp_path):
    decomp = DecomposerOutput(
        subtopics=[SubtopicQuery(subtopic="Transformers", focus="transformer attention")],
        too_complex=False, suggestion="", intent="explanation", is_followup=False,
    )
    mocker.patch("scholr.orchestrator.decompose_query", new_callable=AsyncMock, return_value=decomp)
    expected_state = _make_state("s1", "p1")
    mock_pipeline = mocker.patch(
        "scholr.orchestrator.run_pipeline",
        new_callable=AsyncMock,
        return_value=expected_state,
    )
    mocker.patch("scholr.session.SESSIONS_DIR", tmp_path)

    result = await run_research("explain transformers", "s1")
    assert isinstance(result, ResearchState)
    mock_pipeline.assert_called_once()


def test_merge_states_deduplicates_papers(tmp_path):
    state_a = _make_state("s-0", "p1", "p2")
    state_b = _make_state("s-1", "p2", "p3")

    merged = _merge_states("compare", "s-merged", [state_a, state_b])

    ids = {p.paper_id for p in merged.papers}
    assert ids == {"p1", "p2", "p3"}


def test_merge_states_combines_concept_maps(tmp_path):
    state_a = _make_state("s-0", "p1")
    state_a.concept_to_papers = {"attention": ["p1"]}
    state_b = _make_state("s-1", "p2")
    state_b.concept_to_papers = {"recurrence": ["p2"], "attention": ["p2"]}

    merged = _merge_states("compare", "s-merged", [state_a, state_b])

    assert "p1" in merged.concept_to_papers["attention"]
    assert "p2" in merged.concept_to_papers["attention"]
    assert "p2" in merged.concept_to_papers["recurrence"]
