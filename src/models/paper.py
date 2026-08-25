"""Paper ORM model.

Present from Stage 1 so the schema is ready for Stage 2 (Alembic migrations +
ingestion). It is not queried by the health check, so it has no effect on the
Stage 1 checkpoint.
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


class Paper(Base):
    __tablename__ = "papers"

    arxiv_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    abstract: Mapped[str] = mapped_column(Text)
    authors: Mapped[list] = mapped_column(JSON, default=list)
    categories: Mapped[list] = mapped_column(JSON, default=list)
    pdf_url: Mapped[str] = mapped_column(Text)
    published: Mapped[datetime] = mapped_column(DateTime)
    # Docling output: {"markdown": str, "sections": [{"title", "text"}]}
    parsed_content: Mapped[dict] = mapped_column(JSON, default=dict)
    indexed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_papers_published", "published"),)
