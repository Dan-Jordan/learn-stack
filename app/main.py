from fastapi import FastAPI
from app.routers import notes, query, ask, draft

app = FastAPI(title="LearnStack")
app.include_router(notes.router)
app.include_router(query.router)
app.include_router(ask.router)
app.include_router(draft.router)
