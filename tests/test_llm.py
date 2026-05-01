import pytest
from unittest.mock import AsyncMock, MagicMock
from pydantic import BaseModel
from scholr.llm import llm_parse, LLMRefusalError


class _TestOutput(BaseModel):
    value: str


async def test_llm_parse_returns_parsed_model(mocker):
    mock_msg = MagicMock()
    mock_msg.refusal = None
    mock_msg.parsed = _TestOutput(value="hello")

    mock_choice = MagicMock()
    mock_choice.message = mock_msg

    mock_result = MagicMock()
    mock_result.choices = [mock_choice]

    mock_parse = AsyncMock(return_value=mock_result)
    mocker.patch("scholr.llm.client.beta.chat.completions.parse", mock_parse)

    result = await llm_parse("system", "user", _TestOutput)
    assert isinstance(result, _TestOutput)
    assert result.value == "hello"


async def test_llm_parse_raises_on_refusal(mocker):
    mock_msg = MagicMock()
    mock_msg.refusal = "I cannot help with that."
    mock_msg.parsed = None

    mock_choice = MagicMock()
    mock_choice.message = mock_msg

    mock_result = MagicMock()
    mock_result.choices = [mock_choice]

    mock_parse = AsyncMock(return_value=mock_result)
    mocker.patch("scholr.llm.client.beta.chat.completions.parse", mock_parse)

    with pytest.raises(LLMRefusalError, match="Model refused"):
        await llm_parse("system", "user", _TestOutput)
