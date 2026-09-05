from src.services.opensearch.client import get_opensearch_client
from src.config import get_settings
from opensearchpy import OpenSearch
from pydantic import BaseModel

class OpenSearchResult(BaseModel):
    arxiv_id: str
    title: str
    abstract: str
    score: float

def build_query(query_string: str, categories: list[str] | None, size: int) -> dict:
    """Build an OpenSearch query for the given string."""

    filter_clauses = []
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
                            "fields": ["title^3", "abstract^1"],
                            "type": "best_fields"
                        }
                    }
                ],
                "filter": filter_clauses
            }
        }
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
            abstract=hit["_source"]["abstract"],
            score=hit["_score"]
        )
        results.append(result)

    return results