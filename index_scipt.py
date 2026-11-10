from src.repositories.paper_repository import PaperRepository
from src.services.opensearch.indexing import backfill_index
from src.db import SessionLocal
from src.services.opensearch.chunk_indexing import index_all_papers

with SessionLocal() as session:
    pr = PaperRepository(session=session)
    backfill_index(repo=pr)
    index_all_papers(session=session)