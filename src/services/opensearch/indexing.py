from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk
from src.db import SessionLocal
from src.repositories import PaperRepository
from src.repositories.paper_repository import get_paper_repository
from fastapi import Depends

from src.config import get_settings
from src.models.paper import Paper
from src.services.opensearch.client import get_opensearch_client

def paper_to_document(paper: Paper) -> dict:
    """Convert a Paper SQLAlchemy model instance into the shape our OpenSearch mapping expects."""
    return {
        "_index": get_settings().opensearch.index,
        "_id": paper.arxiv_id, # for idempotency, we use the arxiv_id as the document ID
        "_source": {
            "arxiv_id": paper.arxiv_id,
            "title": paper.title,
            "abstract": paper.abstract,
            "authors": paper.authors,
            "categories": paper.categories,
            "published": paper.published.isoformat(),
        }
    }

def backfill_index(
    repo: PaperRepository | None = Depends(get_paper_repository),
    client: OpenSearch | None = None,
) -> int:
    """Index all papers from Postgres into OpenSearch. Returns count indexed.

    Works both as a FastAPI dependency (repo injected via Depends) and as a
    plain function call from scripts, where the Depends default is never
    resolved and repo needs to be built manually.
    """
    client = client or get_opensearch_client()

    owns_session = not isinstance(repo, PaperRepository)
    session = SessionLocal() if owns_session else None

    try:
        if owns_session:
            repo = PaperRepository(session)

        papers = repo.get_arxiv_articles()
        paper_ids = set()
        actions = []

        for p in papers:
            paper_ids.add(p.arxiv_id)
            actions.append(paper_to_document(p))

        success_count, errors = bulk(client, actions, raise_on_error=False)

        failed_ids = set()
        if errors:
            print(f"{len(errors)} documents failed to index")
            for err in errors:
                action_type = next(iter(err))
                failed_ids.add(err[action_type]["_id"])
                print(err)

        indexedIds = paper_ids - failed_ids
        print(indexedIds)

        repo.update_articles_indexed(ids=indexedIds)
    finally:
        if owns_session:
            session.close()

    return success_count