from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.note import ChatRequest, ChatResponse
from app.assistant import run_assistant

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    # Build the Anthropic-format conversation: prior turns, then the new user message.
    messages = [{"role": m.role, "content": m.content} for m in req.history]
    messages.append({"role": "user", "content": req.message})
    reply, trace = await run_assistant(messages, db)
    return ChatResponse(reply=reply, trace=trace)
