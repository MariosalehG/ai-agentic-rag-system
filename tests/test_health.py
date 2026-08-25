"""Stage 1 test: the app boots and /health answers even with no services running.

Because the health check degrades gracefully, this passes offline: Postgres/OpenSearch/
Ollama get reported as "down: ..." but the endpoint returns 200 and api == "ok".
"""

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health_endpoint_responds() -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["api"] == "ok"
    # keys are always present regardless of service state
    for key in ("postgres", "opensearch", "ollama", "healthy"):
        assert key in body
