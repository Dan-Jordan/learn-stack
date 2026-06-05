from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routers import notes, query, ask, draft

app = FastAPI(title="LearnStack")
app.include_router(notes.router)
app.include_router(query.router)
app.include_router(ask.router)
app.include_router(draft.router)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
async def ui():
    return FileResponse("static/index.html")
