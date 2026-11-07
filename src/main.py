"""FastAPI application entrypoint.

Uses an app factory + lifespan context so startup/shutdown hooks have a clear home as
later stages add index warm-up, connection pools, etc. Routers are registered under a
versioned prefix (/api/v1).
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.routers import health, papers, search, ask

from src.config import get_settings
from src.services.ollama.factory import make_ollama_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    # startup — later stages: ensure OpenSearch index, warm caches, etc.
    app.state.ollama_client = make_ollama_client(app.state.settings)
    yield
    # shutdown — later stages: dispose engine, close redis, etc.


def create_app() -> FastAPI:
    app = FastAPI(
        title="arXiv Paper Curator",
        version="0.1.0",
        description="Production-grade RAG over arXiv papers.",
        lifespan=lifespan,
    )

    app.state.settings = get_settings()

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(papers.router, prefix="/api/v1")
    app.include_router(search.router, prefix="/api/v1")
    app.include_router(ask.router, prefix="/api/v1")
    return app


app = create_app()
