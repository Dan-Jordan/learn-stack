import os
from anthropic import AsyncAnthropic


def _client() -> AsyncAnthropic:
    # Function (not module-level) so the SDK doesn't read ANTHROPIC_API_KEY at import time.
    return AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


async def generate_answer(question: str, context_notes: list) -> str:
    context = "\n\n".join(
        f"[Note: {note.title}]\n{note.content}" for note, _ in context_notes
    )

    system = (
        "You are a technical knowledge assistant. "
        "Answer the question using ONLY the notes provided. "
        "If the notes don't contain relevant information, say so. "
        "Cite notes by title in your answer using [Note: Title] format."
    )

    user_message = f"Notes:\n{context}\n\nQuestion: {question}" if context else f"Question: {question}"

    message = await _client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )

    return message.content[0].text
