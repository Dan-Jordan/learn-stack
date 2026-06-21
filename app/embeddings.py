import logging
import os
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_MODEL = "text-embedding-3-small"


def _client() -> AsyncOpenAI:
    # Function (not module-level) so the SDK doesn't read OPENAI_API_KEY at import time.
    return AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def embed_text(text: str) -> list[float]:
    # DEBUG, not INFO: this fires on every note write and every search — too frequent for INFO.
    # Log the input size only, never the text (it may be sensitive note content).
    logger.debug("Embedding %d chars with %s", len(text), _MODEL)
    try:
        response = await _client().embeddings.create(input=text, model=_MODEL)
    except Exception:
        # The failure is logged with a traceback regardless of this line — by uvicorn when it
        # propagates (/query, /ask, /notes) or by the assistant loop's logger.exception (/chat).
        # This line isn't about visibility; it adds the input size, which the traceback lacks and
        # which distinguishes a token-limit failure from a transient one. No exc_info, to avoid a
        # duplicate traceback alongside the one logged upstream.
        logger.error("Embedding call failed (%d chars, model %s)", len(text), _MODEL)
        raise
    return response.data[0].embedding
