"""Hybrid search: fuse BM25 and vector results via Reciprocal Rank Fusion.

BM25 scores (unbounded, corpus-dependent) and cosine similarity (0–1) live on
incompatible scales, so they can't be added or averaged. RRF discards the raw
scores and uses only rank position: each document earns 1/(k + rank) from each
list it appears in. A document ranked well by both methods accumulates more
than one ranked well by either alone.
"""

from opensearchpy import OpenSearch

from src.services.embeddings.jina import EmbeddingService
from src.services.opensearch.search import OpenSearchResult, bm25_search, vector_search

RRF_K = 60  # standard dampening constant from the original RRF paper


def reciprocal_rank_fusion(
    result_lists: list[list[OpenSearchResult]],
    size: int = 10,
    k: int = RRF_K,
) -> list[OpenSearchResult]:
    scores: dict[str, float] = {}
    docs: dict[str, OpenSearchResult] = {}

    for results in result_lists:
        for rank, doc in enumerate(results):
            key = f"{doc.arxiv_id}::{doc.chunk_text[:60]}"
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            docs[key] = doc

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:size]

    fused = []
    for key, rrf_score in ranked:
        doc = docs[key].model_copy(update={"score": rrf_score})
        fused.append(doc)
    return fused


def hybrid_search(
    query_string: str,
    categories: list[str] | None = None,
    size: int = 10,
    candidate_size: int = 50,
    client: OpenSearch | None = None,
    embedder: EmbeddingService | None = None,
) -> list[OpenSearchResult]:
    """Run BM25 and vector search independently, then fuse the rankings."""
    keyword_results = bm25_search(query_string, categories, candidate_size, client)
    semantic_results = vector_search(query_string, categories, candidate_size, client, embedder)
    return reciprocal_rank_fusion([keyword_results, semantic_results], size=size)