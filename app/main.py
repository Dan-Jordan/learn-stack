import logging
import os

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from app.auth import get_current_user
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

# docs/redoc/openapi are disabled here and re-added below behind auth — router-level
# `dependencies=` doesn't cover FastAPI's built-in doc routes, and leaving the API schema
# publicly browsable would be inconsistent with this app no longer being fully public.
app = FastAPI(title="LearnStack", docs_url=None, redoc_url=None, openapi_url=None)

_auth = [Depends(get_current_user)]

app.include_router(notes.router, dependencies=_auth)
app.include_router(query.router, dependencies=_auth)
app.include_router(ask.router, dependencies=_auth)
app.include_router(draft.router, dependencies=_auth)
app.include_router(assistant.router, dependencies=_auth)
app.include_router(pending.router, dependencies=_auth)
app.include_router(health.router)  # no auth — Render's health check must stay public

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
async def ui(user: str = Depends(get_current_user)):
    return FileResponse("static/index.html")

@app.get("/openapi.json", include_in_schema=False)
async def openapi_json(user: str = Depends(get_current_user)):
    return get_openapi(title=app.title, version=app.version, routes=app.routes)

@app.get("/docs", include_in_schema=False)
async def docs(user: str = Depends(get_current_user)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title=f"{app.title} - Swagger UI")

@app.get("/redoc", include_in_schema=False)
async def redoc(user: str = Depends(get_current_user)):
    return get_redoc_html(openapi_url="/openapi.json", title=f"{app.title} - ReDoc")
