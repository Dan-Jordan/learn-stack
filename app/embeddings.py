from openai import AsyncOpenAI

_client = AsyncOpenAI()
_MODEL = "text-embedding-3-small"


async def embed_text(text: str) -> list[float]:
    response = await _client.embeddings.create(input=text, model=_MODEL)
    return response.data[0].embedding
