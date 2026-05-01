import os
from pydantic import BaseModel
from openai import AsyncOpenAI

MODEL = "gpt-4o"
client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", "test-key-for-unit-tests"))


class LLMRefusalError(Exception):
    pass


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
