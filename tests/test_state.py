import pytest
from pydantic import ValidationError
from scholr.state import (
    Paper, ResearchState, EvidenceClaim, SynthesisResult,
    PlannerOutput, ExpansionOutput, PaperExpansion,
    CoverageOutput, CompressionOutput, PaperCompression,
    existing_ids,
)


def test_paper_model():
    p = Paper(
        paper_id="http://arxiv.org/abs/1706.03762v7",
        title="Attention Is All You Need",
        abstract="We propose the Transformer.",
        source_query="transformer attention",
    )
    assert p.paper_id == "http://arxiv.org/abs/1706.03762v7"


def test_research_state_defaults():
    state = ResearchState(query="test query", session_id="abc-123")
    assert state.papers == []
    assert state.concept_to_papers == {}
    assert state.paper_facts == {}
    assert state.final_output is None
    assert state.depth_reached == 0
    assert state.events == []


def test_existing_ids(sample_paper):
    state = ResearchState(
        query="test", session_id="s1",
        papers=[sample_paper],
    )
    ids = existing_ids(state)
    assert ids == {"http://arxiv.org/abs/1706.03762v7"}


def test_existing_ids_empty():
    state = ResearchState(query="test", session_id="s1")
    assert existing_ids(state) == set()


def test_evidence_claim_requires_paper_ids():
    with pytest.raises(ValidationError):
        EvidenceClaim(claim="some claim", paper_ids=[])


def test_evidence_claim_valid():
    claim = EvidenceClaim(claim="some claim", paper_ids=["p1"])
    assert claim.paper_ids == ["p1"]


def test_planner_output():
    output = PlannerOutput(
        queries=["transformer attention", "self-attention scaling"],
        intent="explanation",
        scope="architecture",
    )
    assert len(output.queries) == 2


def test_expansion_output():
    output = ExpansionOutput(expansions=[
        PaperExpansion(
            paper_id="p1",
            concepts=["self-attention", "positional encoding"],
            follow_up_queries=["attention scaling limits"],
        )
    ])
    assert output.expansions[0].paper_id == "p1"


def test_coverage_output():
    output = CoverageOutput(sufficient=True, missing_aspects=[], extra_queries=[])
    assert output.sufficient is True


def test_compression_output():
    output = CompressionOutput(compressions=[
        PaperCompression(paper_id="p1", key_points=["fact1", "fact2", "fact3"])
    ])
    assert len(output.compressions[0].key_points) == 3


def test_state_serialization_round_trip(sample_synthesis):
    state = ResearchState(
        query="test", session_id="s1",
        final_output=sample_synthesis,
    )
    json_str = state.model_dump_json()
    restored = ResearchState.model_validate_json(json_str)
    assert restored.final_output.final_answer == sample_synthesis.final_answer
