from fastapi import APIRouter

from src.services.opensearch.search import bm25_search, OpenSearchResult, vector_search
from src.services.opensearch.hybrid import hybrid_search
from src.schemas.paper import SearchRequest


router = APIRouter(prefix="/search", tags=["search"])

@router.post("", response_model=list[OpenSearchResult])
def search_papers(
    request: SearchRequest,
) -> list[OpenSearchResult]:
    fn = {
        "keyword": bm25_search,
        "vector": vector_search,
        "hybrid": hybrid_search,
    }
    return fn(request.query, request.categories, request.size)