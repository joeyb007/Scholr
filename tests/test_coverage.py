import pytest
from unittest.mock import AsyncMock
from scholr.coverage import check_coverage
from scholr.state import CoverageOutput, ResearchState, Paper


def _make_state_with_papers() -> ResearchState:
    return ResearchState(
        query="explain transformer architecture",
        session_id="s1",
        papers=[
            Paper(paper_id="p1", title="Attention Is All You Need",
                  abstract="We propose the Transformer.", source_query="q1"),
        ],
    )


async def test_check_coverage_sufficient(mocker):
    expected = CoverageOutput(sufficient=True, missing_aspects=[], extra_queries=[])
    mocker.patch("scholr.coverage.llm_parse", new_callable=AsyncMock, return_value=expected)

    result = await check_coverage(_make_state_with_papers(), lambda _: None)
    assert result.sufficient is True
    assert result.extra_queries == []


async def test_check_coverage_insufficient(mocker):
    expected = CoverageOutput(
        sufficient=False,
        missing_aspects=["positional encoding", "training procedure"],
        extra_queries=["positional encoding transformers", "transformer training warmup"],
    )
    mocker.patch("scholr.coverage.llm_parse", new_callable=AsyncMock, return_value=expected)

    result = await check_coverage(_make_state_with_papers(), lambda _: None)
    assert result.sufficient is False
    assert len(result.extra_queries) == 2


async def test_check_coverage_emits_event(mocker):
    mocker.patch(
        "scholr.coverage.llm_parse",
        new_callable=AsyncMock,
        return_value=CoverageOutput(sufficient=True, missing_aspects=[], extra_queries=[]),
    )
    events = []
    await check_coverage(_make_state_with_papers(), events.append)
    assert any("[Coverage]" in e for e in events)
