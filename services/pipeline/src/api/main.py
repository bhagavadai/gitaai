from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import settings
from .chat import router as chat_router

app = FastAPI(
    title="GitaAI Pipeline",
    description="RAG + Knowledge Graph API for Vedic scripture queries",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
