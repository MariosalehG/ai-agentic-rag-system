"""FastAPI application entrypoint.

Uses an app factory + lifespan context so startup/shutdown hooks have a clear home as
later stages add index warm-up, connection pools, etc. Routers are registered under a
versioned prefix (/api/v1).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.routers import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup — later stages: ensure OpenSearch index, warm caches, etc.
    yield
    # shutdown — later stages: dispose engine, close redis, etc.


def create_app() -> FastAPI:
    app = FastAPI(
        title="arXiv Paper Curator",
        version="0.1.0",
        description="Production-grade RAG over arXiv papers.",
        lifespan=lifespan,
    )
    app.include_router(health.router, prefix="/api/v1")
    return app


app = create_app()
