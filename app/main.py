from fastapi import FastAPI
from app.routers import notes

app = FastAPI(title="LearnStack")
app.include_router(notes.router)
