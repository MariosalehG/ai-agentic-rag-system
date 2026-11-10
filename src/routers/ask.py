from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.services.ollama.context import build_prompt, format_context
from src.services.opensearch.hybrid import hybrid_search

from src.dependencies import OllamaDep

from src.services.cache.redis_cache import cache_get, cache_set, make_key

router = APIRouter(tags=["rag"])

SYSTEM_PROMPT = Path("src/services/ollama/prompts/rag_system.txt").read_text()

ANSWER_TTL = 3600  # seconds to cache answers


class AskRequest(BaseModel):
    query: str
    categories: list[str] | None = None
    size: int = Field(default=5, ge=1, le=20)


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    chunks_used: int


@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest, llm: OllamaDep) -> AskResponse:
    cache_key = make_key("answer", {
        "query": request.query,
        "categories": request.categories,
        "size": request.size
    })

    if(cache_get(cache_key) is not None):
        return AskResponse(**cache_get(cache_key))


    results = hybrid_search(request.query, request.categories, request.size)

    if not results:
        return AskResponse(
            answer="No relevant papers found for that question.",
            sources=[],
            chunks_used=0,
        )

    context = format_context(results)
    prompt = build_prompt(request.query, context)
    answer = await llm.generate(prompt, SYSTEM_PROMPT)

    # dict.fromkeys preserves retrieval order while de-duplicating
    sources = list(dict.fromkeys(r.arxiv_id for r in results))

    response = AskResponse(answer=answer, sources=sources, chunks_used=len(results))

    cache_set(cache_key, response.model_dump(), ttl=ANSWER_TTL)  # cache for 1 hour

    return response


@router.post("/stream")
async def ask_stream(request: AskRequest, llm: OllamaDep) -> StreamingResponse:
    results = hybrid_search(request.query, request.categories, request.size)
    context = format_context(results)
    prompt = build_prompt(request.query, context)

    async def token_generator():
        async for token in llm.stream(prompt, SYSTEM_PROMPT):
            yield token

    return StreamingResponse(token_generator(), media_type="text/plain")