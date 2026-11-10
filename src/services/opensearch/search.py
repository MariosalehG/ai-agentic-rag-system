from src.services.opensearch.client import get_opensearch_client
from src.config import get_settings
from opensearchpy import OpenSearch
from pydantic import BaseModel
from src.services.embeddings.jina import EmbeddingService

class OpenSearchResult(BaseModel):
    arxiv_id: str
    title: str
    chunk_text: str 
    abstract: str
    score: float

def build_query(query_string: str, categories: list[str] | None, size: int) -> dict:
    """Build an OpenSearch query for the given string."""

    # paper-level docs from backfill_index have no chunk_text; search chunks only
    filter_clauses = [{"exists": {"field": "chunk_text"}}]
    if categories:
        filter_clauses.append({
            "terms": {
                "categories": categories
            }
        })
    
    return {
        "size": size,
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query_string,
                            "fields": ["title^3", "abstract^2", "chunk_text^1"],
                            "type": "best_fields"
                        }
                    }
                ],
                "filter": filter_clauses
            }
        }
    }

def build_knn_query(query_vector: list[float], categories: list[str] | None, size: int) -> dict:
    """Build an OpenSearch KNN query against the embedding field."""
    
    knn_clause = {
        "knn": {
            "embedding": {
                "vector": query_vector,
                "k": size
            }
        }
    }

    # Filters combine with knn inside a bool query; always restrict to chunk docs
    filter_clauses = [{"exists": {"field": "chunk_text"}}]
    if categories:
        filter_clauses.append({"terms": {"categories": categories}})

    return {
        "size": size,
        "query": {
            "bool": {
                "must": [knn_clause],
                "filter": filter_clauses,
            }
        },
    }


def bm25_search(query_string: str, categories: list[str] | None = None, size: int = 10, client: OpenSearch | None = None) -> list[OpenSearchResult]:
    """Perform a BM25 search on OpenSearch for the given query string and optional categories."""
    client = client or get_opensearch_client()
    query = build_query(query_string, categories, size)
    response = client.search(index=get_settings().opensearch.index, body=query)

    results = []

    for hit in response["hits"]["hits"]:
        result = OpenSearchResult(
            arxiv_id=hit["_source"]["arxiv_id"],
            title=hit["_source"]["title"],
            chunk_text=hit["_source"]["chunk_text"],
            abstract=hit["_source"]["abstract"],
            score=hit["_score"]
        )
        results.append(result)

    return results


def vector_search(
    query_string: str,
    categories: list[str] | None = None,
    size: int = 10,
    client: OpenSearch | None = None,
    embedder: EmbeddingService | None = None,
) -> list[OpenSearchResult]:
    """Semantic search: embed the query, find the nearest chunk vectors."""
    client = client or get_opensearch_client()
    embedder = embedder or EmbeddingService()

    query_vector = embedder.embed_query(query_string)
    body = build_knn_query(query_vector, categories, size)
    response = client.search(index=get_settings().opensearch.index, body=body)

    return [
        OpenSearchResult(
            arxiv_id=hit["_source"]["arxiv_id"],
            title=hit["_source"]["title"],
            chunk_text=hit["_source"]["chunk_text"],
            abstract=hit["_source"]["abstract"],
            score=hit["_score"],
        )
        for hit in response["hits"]["hits"]
    ]