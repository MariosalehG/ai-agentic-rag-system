"""Read endpoints over stored papers: a slim list view and a full detail view."""

from fastapi import APIRouter, HTTPException, Query

from src.models.paper import Paper
from src.schemas import PaperDetail, PaperSummary

from src.repositories.paper_repository import PaperRepository, get_paper_repository

from fastapi import Depends

router = APIRouter(prefix="/papers", tags=["papers"])


@router.get("", response_model=list[PaperSummary])
def list_papers(
    limit: int = Query(20, ge=1, le=100),
    repo: PaperRepository = Depends(get_paper_repository)
) -> list[Paper]:
    return repo.get_arxiv_articles(limit=limit)


@router.get("/{arxiv_id}", response_model=PaperDetail)
def get_paper(
        arxiv_id: str,
        repo: PaperRepository = Depends(get_paper_repository)
    ) -> Paper:
        paper = repo.get_by_arxiv_id(arxiv_id)
        if paper is None:
            raise HTTPException(status_code=404, detail=f"Paper '{arxiv_id}' not found")
        return paper
