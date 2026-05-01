import pytest
from unittest.mock import AsyncMock
from scholr.expansion import expand_papers, merge_expansions
from scholr.state import (
    ExpansionOutput, PaperExpansion, ResearchState, Paper
)


def _make_state(*paper_ids: str) -> ResearchState:
    return ResearchState(
        query="test", session_id="s1",
        papers=[
            Paper(paper_id=pid, title=f"T{pid}", abstract=f"A{pid}", source_query="q")
            for pid in paper_ids
        ],
    )


async def test_expand_papers_returns_output(mocker):
    state = _make_state("p1")
    expected = ExpansionOutput(expansions=[
        PaperExpansion(paper_id="p1", concepts=["attention"], follow_up_queries=["attention limits"])
    ])
    mocker.patch("scholr.expansion.llm_parse", new_callable=AsyncMock, return_value=expected)

    result = await expand_papers(state, lambda _: None)
    assert len(result.expansions) == 1
    assert result.expansions[0].paper_id == "p1"


def test_merge_expansions_updates_concept_map():
    state = _make_state("p1", "p2")
    output = ExpansionOutput(expansions=[
        PaperExpansion(paper_id="p1", concepts=["self-attention", "positional encoding"], follow_up_queries=["q1"]),
        PaperExpansion(paper_id="p2", concepts=["self-attention"], follow_up_queries=["q2"]),
    ])
    merge_expansions(state, output)

    assert "self-attention" in state.concept_to_papers
    assert "p1" in state.concept_to_papers["self-attention"]
    assert "p2" in state.concept_to_papers["self-attention"]
    assert "positional encoding" in state.concept_to_papers
    assert "p1" in state.concept_to_papers["positional encoding"]


def test_merge_expansions_deduplicates_follow_up_queries():
    state = _make_state("p1", "p2")
    output = ExpansionOutput(expansions=[
        PaperExpansion(paper_id="p1", concepts=["c1"], follow_up_queries=["shared query", "unique1"]),
        PaperExpansion(paper_id="p2", concepts=["c2"], follow_up_queries=["shared query", "unique2"]),
    ])
    follow_ups = merge_expansions(state, output)

    assert follow_ups.count("shared query") == 1
    assert "unique1" in follow_ups
    assert "unique2" in follow_ups


def test_merge_expansions_does_not_duplicate_paper_in_concept():
    state = _make_state("p1")
    state.concept_to_papers["self-attention"] = ["p1"]
    output = ExpansionOutput(expansions=[
        PaperExpansion(paper_id="p1", concepts=["self-attention"], follow_up_queries=[]),
    ])
    merge_expansions(state, output)
    assert state.concept_to_papers["self-attention"].count("p1") == 1
