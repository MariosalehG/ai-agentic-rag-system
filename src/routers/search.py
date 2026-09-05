from fastapi import APIRouter

from src.services.opensearch.search import bm25_search, OpenSearchResult
from src.schemas.paper import SearchRequest


router = APIRouter(prefix="/search", tags=["search"])

@router.post("", response_model=list[OpenSearchResult])
def search_papers(
    query: SearchRequest,
) -> list[OpenSearchResult]:
    return bm25_search(query_string=query.query, categories=query.categories, size=query.size)