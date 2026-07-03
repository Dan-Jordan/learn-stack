import logging
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routers import notes, query, ask, draft, assistant, health, pending

# Central logging config. The level is driven by LOG_LEVEL (default INFO) so verbosity can be
# turned up/down on Render without a code change; an unrecognized value falls back to INFO
# rather than crashing startup. The format adds a timestamp and the emitting logger's name, so
# each line shows when it happened and which module it came from
# (e.g. "2026-06-21 12:00:00 INFO app.crud.notes: note created ...").
_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# httpx logs every outbound HTTP request at INFO (one line per Anthropic/OpenAI call);
# raise its floor to WARNING so our own INFO logs aren't drowned out.
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(title="LearnStack")
app.include_router(notes.router)
app.include_router(query.router)
app.include_router(ask.router)
app.include_router(draft.router)
app.include_router(assistant.router)
app.include_router(pending.router)
app.include_router(health.router)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
async def ui():
    return FileResponse("static/index.html")
