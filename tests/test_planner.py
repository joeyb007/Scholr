import pytest
from unittest.mock import AsyncMock
from scholr.planner import plan_queries
from scholr.state import PlannerOutput, ResearchState


async def test_plan_queries_returns_queries(mocker, sample_state):
    expected = PlannerOutput(
        queries=["transformer attention mechanism", "self-attention scaling"],
        intent="explanation",
        scope="architecture",
    )
    mocker.patch("scholr.planner.llm_parse", new_callable=AsyncMock, return_value=expected)

    queries = await plan_queries(sample_state, lambda _: None)
    assert queries == ["transformer attention mechanism", "self-attention scaling"]


async def test_plan_queries_includes_concept_context(mocker, sample_state):
    sample_state.concept_to_papers["self-attention"] = ["p1"]
    expected = PlannerOutput(queries=["positional encoding"], intent="explanation", scope="architecture")

    mock_llm = mocker.patch("scholr.planner.llm_parse", new_callable=AsyncMock, return_value=expected)
    await plan_queries(sample_state, lambda _: None)

    call_args = mock_llm.call_args
    user_prompt = call_args.args[1]
    assert "self-attention" in user_prompt


async def test_plan_queries_emits_event(mocker, sample_state):
    mocker.patch(
        "scholr.planner.llm_parse",
        new_callable=AsyncMock,
        return_value=PlannerOutput(queries=["q1"], intent="x", scope="y"),
    )
    events = []
    await plan_queries(sample_state, events.append)
    assert any("[Planner]" in e for e in events)
