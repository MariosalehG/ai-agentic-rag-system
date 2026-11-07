from src.config import Settings, get_settings
from typing import Annotated
from fastapi import Depends, Request
from src.services.ollama.client import OllamaClient
from src.repositories import PaperRepository
from sqlalchemy.orm import Session
from src.db import get_db

def get_ollama_client(request: Request) -> OllamaClient:
    """Get Ollama client from the request state."""
    return request.app.state.ollama_client




SettingsDep = Annotated[Settings, Depends(get_settings)]
OllamaDep = Annotated[OllamaClient, Depends(get_ollama_client)]
DbSessionDep = Annotated[Session, Depends(get_db)]


def get_paper_repository(session: DbSessionDep) -> PaperRepository:
    return PaperRepository(session)

PaperRepoDep = Annotated[PaperRepository, Depends(get_paper_repository)]

