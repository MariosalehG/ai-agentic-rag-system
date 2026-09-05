"""API response shapes for Paper.

Split in two so the list endpoint stays cheap: PaperSummary omits parsed_content,
which can be several MB of Docling markdown per paper, while PaperDetail includes
everything for the single-paper view. Both read directly off the ORM object via
`from_attributes=True` instead of the route having to unpack fields by hand.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PaperSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    arxiv_id: str
    title: str
    authors: list[str]
    categories: list[str]
    published: datetime


class PaperDetail(PaperSummary):
    abstract: str
    pdf_url: str
    parsed_content: dict[str, object]
    indexed: bool
    created_at: datetime


class SearchRequest(BaseModel):
    query: str
    categories: list[str] | None = None
    size: int = Field(default=10, le=100, ge=1, description="Number of results to return (max 100)")