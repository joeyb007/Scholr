import os
from pydantic import BaseModel
from openai import AsyncOpenAI, AuthenticationError

MODEL = "gpt-4o-mini"
client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", "test-key-for-unit-tests"))


class LLMRefusalError(Exception):
    pass


def get_client() -> AsyncOpenAI:
    return client


def set_api_key(key: str) -> None:
    global client
    os.environ["OPENAI_API_KEY"] = key
    client = AsyncOpenAI(api_key=key)


async def validate_api_key() -> bool:
    try:
        await get_client().models.list()
        return True
    except AuthenticationError:
        return False


async def llm_parse(
    system: str,
    user: str,
    response_format: type[BaseModel],
) -> BaseModel:
    result = await client.beta.chat.completions.parse(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format=response_format,
    )
    msg = result.choices[0].message
    if msg.refusal:
        raise LLMRefusalError(f"Model refused: {msg.refusal}")
    return msg.parsed
