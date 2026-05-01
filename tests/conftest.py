import pytest
from scholr.state import (
    Paper, ResearchState, SynthesisResult, EvidenceClaim
)


@pytest.fixture
def sample_paper() -> Paper:
    return Paper(
        paper_id="http://arxiv.org/abs/1706.03762v7",
        title="Attention Is All You Need",
        abstract="We propose the Transformer, a model architecture eschewing recurrence.",
        source_query="transformer attention mechanism",
    )


@pytest.fixture
def sample_state(sample_paper) -> ResearchState:
    return ResearchState(
        query="explain transformer architecture",
        session_id="test-session-001",
        papers=[sample_paper],
    )


@pytest.fixture
def sample_synthesis() -> SynthesisResult:
    return SynthesisResult(
        final_answer="Transformers use self-attention to process sequences.",
        key_concepts=["self-attention", "positional encoding"],
        intuition="Replace recurrence with attention over all positions.",
        mechanism="Queries, keys, and values compute weighted context vectors.",
        limitations="Quadratic complexity with sequence length.",
        open_questions="Can attention be made linear without quality loss?",
        evidence_map=[
            EvidenceClaim(
                claim="Self-attention enables parallel computation.",
                paper_ids=["http://arxiv.org/abs/1706.03762v7"],
            )
        ],
        papers_used=1,
        depth_reached=0,
    )
