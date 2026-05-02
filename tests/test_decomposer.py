import pytest
from unittest.mock import AsyncMock
from scholr.decomposer import decompose_query
from scholr.state import DecomposerOutput, SubtopicQuery


async def test_decompose_single_topic(mocker):
    expected = DecomposerOutput(
        subtopics=[SubtopicQuery(subtopic="Transformers", focus="transformer self attention mechanism")],
        too_complex=False,
        suggestion="",
        intent="explanation",
        is_followup=False,
    )
    mocker.patch("scholr.decomposer.llm_parse", new_callable=AsyncMock, return_value=expected)

    result = await decompose_query("explain transformers", lambda _: None)
    assert result.too_complex is False
    assert len(result.subtopics) == 1
    assert result.subtopics[0].subtopic == "Transformers"


async def test_decompose_comparison(mocker):
    expected = DecomposerOutput(
        subtopics=[
            SubtopicQuery(subtopic="CNNs", focus="convolutional neural networks image classification"),
            SubtopicQuery(subtopic="RNNs", focus="recurrent neural networks sequence modeling"),
        ],
        too_complex=False,
        suggestion="",
        intent="comparison",
        is_followup=False,
    )
    mocker.patch("scholr.decomposer.llm_parse", new_callable=AsyncMock, return_value=expected)

    result = await decompose_query("contrast CNNs and RNNs", lambda _: None)
    assert result.too_complex is False
    assert len(result.subtopics) == 2
    assert result.intent == "comparison"


async def test_decompose_too_complex(mocker):
    expected = DecomposerOutput(
        subtopics=[],
        too_complex=True,
        suggestion="Try: 'explain CNNs', 'explain RNNs', or 'compare CNNs and RNNs'",
        intent="survey",
        is_followup=False,
    )
    mocker.patch("scholr.decomposer.llm_parse", new_callable=AsyncMock, return_value=expected)

    result = await decompose_query(
        "explain all neural network architectures and quantum computing and cognitive science",
        lambda _: None,
    )
    assert result.too_complex is True
    assert result.suggestion != ""
    assert result.subtopics == []


async def test_decompose_emits_events(mocker):
    expected = DecomposerOutput(
        subtopics=[SubtopicQuery(subtopic="Transformers", focus="transformer attention")],
        too_complex=False,
        suggestion="",
        intent="explanation",
        is_followup=False,
    )
    mocker.patch("scholr.decomposer.llm_parse", new_callable=AsyncMock, return_value=expected)

    events = []
    await decompose_query("explain transformers", events.append)
    assert any("[Orchestrator]" in e for e in events)
