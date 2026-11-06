from src.services.opensearch.search import OpenSearchResult


def format_context(results: list[OpenSearchResult], max_chars: int = 8000) -> str:
    """Format retrieved chunks into a context block for the LLM prompt.

    Truncates at max_chars because every token costs latency — prompt size is
    the cheapest large speedup available in a RAG pipeline.
    """
    parts: list[str] = []
    total = 0

    for r in results:
        block = f"[{r.arxiv_id}] (from: {r.title})\n{r.chunk_text}"
        if total + len(block) > max_chars:
            break
        parts.append(block)
        total += len(block)

    return "\n\n---\n\n".join(parts)


def build_prompt(question: str, context: str) -> str:
    return f"""Context from research papers:

{context}

---

Question: {question}

Answer:"""