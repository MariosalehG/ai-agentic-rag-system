"""Repository for persisting arXiv articles as Paper rows.

Keeps SQL/upsert details out of the scraper (which only knows about arXiv) and out of
callers (DAGs, scripts, routers), which should only need to hand over ArxivArticle
objects and get Paper rows back.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, defer
from sqlalchemy import update

from src.models.paper import Paper
from src.services.arxiv.arxiv_scraper import ArxivArticle

from fastapi import Depends
from src.db import get_db

# Columns refreshed when a paper is re-ingested. `indexed` and `created_at` are
# deliberately excluded: re-ingesting shouldn't reset a paper's search-index status or
# its original creation timestamp.
_UPSERT_COLUMNS = (
    "title",
    "abstract",
    "authors",
    "categories",
    "pdf_url",
    "published",
    "parsed_content",
)


class PaperRepository:
    def __init__(self, session: Session):
        self._session = session

    def get_by_arxiv_id(self, arxiv_id: str) -> Paper | None:
        return self._session.get(Paper, arxiv_id)

    def get_arxiv_articles(self, limit: int = 5) -> list[ArxivArticle]:
        """Return all stored papers as ArxivArticle objects."""
        query = (
            select(Paper)
            .options(defer(Paper.parsed_content))
            .order_by(Paper.published.desc())
            .limit(limit)
        )
        rows = self._session.execute(query).scalars().all()
        return [
            ArxivArticle(
                arxiv_id=row.arxiv_id,
                title=row.title,
                abstract=row.abstract,
                authors=row.authors,
                categories=row.categories,
                pdf_url=row.pdf_url or None,
                published=row.published,
            )
            for row in rows
        ]

    def upsert(self, article: ArxivArticle) -> Paper:
        return self.upsert_many([article])[0]

    def upsert_many(self, articles: Sequence[ArxivArticle]) -> list[Paper]:
        """Insert articles, updating existing rows (matched on arxiv_id) in place."""
        if not articles:
            return []

        now = datetime.now(UTC)
        values = [
            {
                "arxiv_id": a.arxiv_id,
                "title": a.title,
                "abstract": a.abstract,
                "authors": a.authors,
                "categories": a.categories,
                "pdf_url": a.pdf_url or "",
                "published": a.published,
                "parsed_content": {"markdown": a.parsed_content} if a.parsed_content else {},
                "indexed": False,
                "created_at": now,
            }
            for a in articles
        ]

        stmt = insert(Paper).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Paper.arxiv_id],
            set_={col: stmt.excluded[col] for col in _UPSERT_COLUMNS},
        )
        self._session.execute(stmt)
        self._session.commit()

        arxiv_ids = [a.arxiv_id for a in articles]
        query = select(Paper).where(Paper.arxiv_id.in_(arxiv_ids))
        rows = self._session.execute(query).scalars().all()
        by_id = {row.arxiv_id: row for row in rows}
        return [by_id[arxiv_id] for arxiv_id in arxiv_ids]

    def update_articles_indexed(self ,ids: list[str]):
        stmt = (
            update(Paper)
            .where(Paper.arxiv_id.in_(ids))
            .values(indexed=True)
        )
        self._session.execute(stmt)
        self._session.commit()


def get_paper_repository(session: Session = Depends(get_db)):
        """Return a PaperRepository instance for the given session."""
        return PaperRepository(session)