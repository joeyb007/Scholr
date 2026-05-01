import pytest
from unittest.mock import AsyncMock, MagicMock
from scholr.synthesis import synthesize, stream_answer
from scholr.state import (
    EvidenceClaim, ResearchState, SynthesisResult, Paper
)


def _make_state() -> ResearchState:
    return ResearchState(
        query="explain transformer architecture",
        session_id="s1",
        papers=[
            Paper(paper_id="p1", title="Attention Is All You Need",
                  abstract="We propose the Transformer.", source_query="q1"),
        ],
        paper_facts={"p1": ["Self-attention replaces recurrence.", "Enables parallelization."]},
        concept_to_papers={"self-attention": ["p1"]},
        depth_reached=1,
    )


async def test_synthesize_returns_result(mocker, sample_synthesis):
    mocker.patch("scholr.synthesis.llm_parse", new_callable=AsyncMock, return_value=sample_synthesis)
    result = await synthesize(_make_state(), lambda _: None)
    assert isinstance(result, SynthesisResult)
    assert result.final_answer != ""


async def test_synthesize_passes_paper_ids_in_prompt(mocker, sample_synthesis):
    mock_llm = mocker.patch(
        "scholr.synthesis.llm_parse", new_callable=AsyncMock, return_value=sample_synthesis
    )
    await synthesize(_make_state(), lambda _: None)
    user_prompt = mock_llm.call_args.args[1]
    assert "p1" in user_prompt


async def test_synthesize_emits_event(mocker, sample_synthesis):
    mocker.patch("scholr.synthesis.llm_parse", new_callable=AsyncMock, return_value=sample_synthesis)
    events = []
    await synthesize(_make_state(), events.append)
    assert any("[Synthesis]" in e for e in events)


async def test_stream_answer_calls_on_token_and_returns_full_text(mocker):
    async def fake_stream():
        for word in ["The ", "Transformer ", "uses ", "self-attention."]:
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta.content = word
            yield chunk

    mocker.patch(
        "scholr.synthesis.client.chat.completions.create",
        new_callable=AsyncMock,
        return_value=fake_stream(),
    )

    tokens = []
    result = await stream_answer(_make_state(), tokens.append)

    assert result == "The Transformer uses self-attention."
    assert tokens == ["The ", "Transformer ", "uses ", "self-attention."]


async def test_stream_answer_skips_empty_deltas(mocker):
    async def fake_stream():
        for content in ["hello", None, "", " world"]:
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta.content = content
            yield chunk

    mocker.patch(
        "scholr.synthesis.client.chat.completions.create",
        new_callable=AsyncMock,
        return_value=fake_stream(),
    )

    tokens = []
    result = await stream_answer(_make_state(), tokens.append)

    assert result == "hello world"
    assert tokens == ["hello", " world"]
