import os
from openai import AsyncOpenAI

_MODEL = "text-embedding-3-small"


def _client() -> AsyncOpenAI:
    # Function (not module-level) so the SDK doesn't read OPENAI_API_KEY at import time.
    return AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def embed_text(text: str) -> list[float]:
    response = await _client().embeddings.create(input=text, model=_MODEL)
    return response.data[0].embedding
