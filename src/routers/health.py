"""Health check that actually probes dependencies.

A static {"ok": true} tells you nothing. This endpoint verifies Postgres, OpenSearch,
and Ollama independently and degrades gracefully: if a service is down it reports the
reason instead of raising, so the endpoint itself always answers 200. The aggregate
`healthy` flag is the single thing to watch during Stage 1 bring-up.
"""

import httpx
from fastapi import APIRouter
from sqlalchemy import text

from src.config import get_settings
from src.db import engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    s = get_settings()
    status: dict[str, object] = {"api": "ok"}

    # Postgres
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        status["postgres"] = "ok"
    except Exception as exc:  # noqa: BLE001 - report, don't crash
        status["postgres"] = f"down: {exc}"

    # HTTP-based services
    checks = {
        "opensearch": f"{s.opensearch.host}/_cluster/health",
        "ollama": f"{s.ollama.host}/api/tags",
    }
    async with httpx.AsyncClient(timeout=3) as client:
        for name, url in checks.items():
            try:
                resp = await client.get(url)
                status[name] = "ok" if resp.status_code == 200 else f"http {resp.status_code}"
            except Exception as exc:  # noqa: BLE001
                status[name] = f"down: {exc}"

    status["healthy"] = all(v == "ok" for k, v in status.items() if k != "healthy")
    return status
