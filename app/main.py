import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routers import notes, query, ask, draft, assistant, health

# Central logging config: sets the cutoff level AND installs a formatter that
# renders the logger name + level (e.g. "ERROR:app.assistant:..."), not just the message.
logging.basicConfig(level=logging.INFO)
# httpx logs every outbound HTTP request at INFO (one line per Anthropic/OpenAI call);
# raise its floor to WARNING so our own INFO logs aren't drowned out.
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(title="LearnStack")
app.include_router(notes.router)
app.include_router(query.router)
app.include_router(ask.router)
app.include_router(draft.router)
app.include_router(assistant.router)
app.include_router(health.router)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
async def ui():
    return FileResponse("static/index.html")
