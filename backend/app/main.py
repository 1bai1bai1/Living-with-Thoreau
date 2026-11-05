"""Living with Thoreau: the game server."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import game

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Living with Thoreau", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(game.router, prefix="/api")


@app.get("/api/health")
async def health_check() -> dict:
    return {"status": "healthy", "llm": "gemini" if get_settings().use_gemini else "mock"}
