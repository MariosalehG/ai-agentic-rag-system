"""Jina AI embeddings client.

Converts text into 1024-dimensional vectors for semantic search. Batches
requests because embedding one chunk at a time would be needlessly slow and
burn through rate limits.
"""

import time

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.config import get_settings

JINA_URL = "https://api.jina.ai/v1/embeddings"
JINA_MODEL = "jina-embeddings-v3"
EMBEDDING_DIM = 1024
BATCH_SIZE = 64
BATCH_DELAY_SECONDS = 2  # pause between batches to stay under the rate limit

_backoff = wait_exponential(multiplier=2, min=5, max=60)


def _is_retryable(exc: BaseException) -> bool:
    """Retry timeouts, 429s and 5xx; permanent 4xx errors (401, 422...) fail fast."""
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status == 429 or status >= 500
    return False


def _wait(retry_state) -> float:
    """Honor the Retry-After header on 429s, otherwise back off exponentially."""
    exc = retry_state.outcome.exception()
    if isinstance(exc, httpx.HTTPStatusError):
        retry_after = exc.response.headers.get("Retry-After")
        if retry_after and retry_after.isdigit():
            return float(retry_after)
    return _backoff(retry_state)


class EmbeddingService:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or get_settings().jina_api_key
        if not self.api_key:
            raise RuntimeError("JINA_API_KEY is not set — add it to your .env")

    @retry(
        stop=stop_after_attempt(8),
        wait=_wait,
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = httpx.post(
            JINA_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": JINA_MODEL,
                "task": "retrieval.passage",
                "input": texts,
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()["data"]
        # Jina returns results with an "index" field — sort to guarantee order
        data.sort(key=lambda d: d["index"])
        return [item["embedding"] for item in data]

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts, batching automatically. Order is preserved."""
        if not texts:
            return []

        vectors: list[list[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            if i:
                time.sleep(BATCH_DELAY_SECONDS)
            batch = texts[i : i + BATCH_SIZE]
            vectors.extend(self._embed_batch(batch))
        return vectors

    def embed_query(self, query: str) -> list[float]:
        """Embed a single search query.

        Uses task='retrieval.query' rather than 'retrieval.passage' — Jina v3
        optimizes these differently, and matching the task to the use case
        measurably improves retrieval quality.
        """
        response = httpx.post(
            JINA_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": JINA_MODEL,
                "task": "retrieval.query",
                "input": [query],
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]