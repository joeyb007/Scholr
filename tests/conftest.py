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
        authors="Vaswani, A., Shazeer, N., Parmar, N. et al.",
        year=2017,
        venue="Advances in Neural Information Processing Systems",
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
        answer_paragraphs=["Transformers use self-attention [1] to process sequences in parallel."],
        follow_up_questions=[
            "How does positional encoding work in transformers?",
            "What are the memory requirements of multi-head attention?",
            "How do vision transformers differ from language transformers?",
        ],
    )
