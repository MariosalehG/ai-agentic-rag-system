"""Chunk-level indexing: one paper becomes many OpenSearch documents.

Each document holds one chunk's text plus its embedding, denormalized with
the parent paper's metadata so search results are self-contained.
"""

from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk
from sqlalchemy.orm import Session

from src.config import get_settings
from src.models.paper import Paper
from src.services.embeddings.jina import EmbeddingService
from src.services.indexing.text_chunker import chunk_sections
from src.services.opensearch.client import get_opensearch_client


def paper_is_indexed(arxiv_id: str, client: OpenSearch) -> bool:
    """True if the paper already has at least one chunk in the index."""
    result = client.count(
        index=get_settings().opensearch.index,
        body={"query": {"bool": {"filter": [
            {"term": {"arxiv_id": arxiv_id}},
            # paper-level docs from backfill_index share the arxiv_id; only chunks count
            {"exists": {"field": "chunk_text"}},
        ]}}},
    )
    return result["count"] > 0


def delete_paper_chunks(arxiv_id: str, client: OpenSearch) -> None:
    """Remove all existing chunks for a paper, preventing stale orphans."""
    client.delete_by_query(
        index=get_settings().opensearch.index,
        body={"query": {"term": {"arxiv_id": arxiv_id}}},
        refresh=True,
    )


def build_chunk_documents(
    paper: Paper,
    chunks: list[dict],
    embeddings: list[list[float]],
) -> list[dict]:
    """Pair each chunk with its embedding and the parent paper's metadata."""
    index_name = get_settings().opensearch.index
    docs = []

    for chunk, vector in zip(chunks, embeddings, strict=True):
        docs.append({
            "_index": index_name,
            "_id": f"{paper.arxiv_id}_{chunk['chunk_index']}_{chunk['section_title'][:20]}",
            "_source": {
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "abstract": paper.abstract,
                "authors": paper.authors,
                "categories": paper.categories,
                "published": paper.published.isoformat(),
                "chunk_text": chunk["text"],
                "section_title": chunk["section_title"],
                "chunk_index": chunk["chunk_index"],
                "embedding": vector,
            },
        })

    return docs


def index_paper_chunks(
    paper: Paper,
    embedder: EmbeddingService,
    client: OpenSearch,
    max_words: int = 300,
    overlap: int = 40,
) -> int:
    """Chunk, embed, and index a single paper. Returns chunks indexed."""
    sections = paper.parsed_content
    if not sections:
        print(f"  {paper.arxiv_id}: no parsed content, skipping")
        return 0

    chunks = chunk_sections(sections, max_words=max_words, overlap=overlap)
    if not chunks:
        print(f"  {paper.arxiv_id}: produced no chunks, skipping")
        return 0

    texts = [c["text"] for c in chunks]
    embeddings = embedder.embed(texts)

    delete_paper_chunks(paper.arxiv_id, client)

    docs = build_chunk_documents(paper, chunks, embeddings)
    success_count, errors = bulk(client, docs, raise_on_error=False)

    if errors:
        print(f"  {paper.arxiv_id}: {len(errors)} chunks failed")
        for err in errors[:3]:
            print("   ", err)

    print(f"  {paper.arxiv_id}: {success_count}/{len(chunks)} chunks indexed")
    return success_count


def index_all_papers(
    db: Session,
    client: OpenSearch | None = None,
    embedder: EmbeddingService | None = None,
    skip_existing: bool = True,
) -> int:
    """Chunk, embed, and index every paper in Postgres.

    With skip_existing, papers that already have chunks in OpenSearch are
    skipped, so a rerun after a failure only embeds what's missing. Pass
    skip_existing=False to re-chunk everything (e.g. after changing chunk size).
    """
    client = client or get_opensearch_client()
    embedder = embedder or EmbeddingService()

    papers = db.query(Paper).all()
    print(f"Indexing {len(papers)} papers...")

    total = 0
    failed: list[str] = []

    for p in papers:
        if skip_existing and paper_is_indexed(p.arxiv_id, client):
            print(f"  {p.arxiv_id}: already indexed, skipping")
            continue
        try:
            total += index_paper_chunks(p, embedder, client)
        except Exception as e:
            # One bad paper shouldn't abort the rest; rerun to pick up failures.
            print(f"  {p.arxiv_id}: FAILED ({type(e).__name__}: {e})")
            failed.append(p.arxiv_id)

    print(f"\nTotal chunks indexed: {total}")
    if failed:
        print(f"Failed papers ({len(failed)}): {failed} - rerun to retry them")
    return total