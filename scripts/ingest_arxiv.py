"""Manual launcher for arXiv ingestion: fetch papers and upsert them into Postgres.

This is the manual stand-in for the Airflow DAG that later stages automate. Run it
from the project root (so `src` is importable) with `uv run` or the project's venv:

    uv run python scripts/ingest_arxiv.py --category cs.AI --max-results 20
"""

import argparse
import logging

from src.db import SessionLocal
from src.repositories import PaperRepository
from src.services.arxiv.arxiv_scraper import ArxivScraper

logger = logging.getLogger(__name__)


def build_search_query(category: str, max_results: int) -> str:
    return (
        f"search_query=cat:{category}"
        "&sortBy=submittedDate&sortOrder=descending"
        f"&max_results={max_results}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--category", default="cs.AI", help="arXiv category to query, e.g. cs.AI")
    parser.add_argument("--max-results", type=int, default=5, help="Number of papers to fetch")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    scraper = ArxivScraper()
    search_query = build_search_query(args.category, args.max_results)
    articles = scraper.fetch_articles(search_query=search_query)
    logger.info("Fetched %d articles from arXiv", len(articles))

    with SessionLocal() as session:
        papers = PaperRepository(session).upsert_many(articles)

    logger.info("Upserted %d papers into the database", len(papers))
    for paper in papers:
        print(f"{paper.arxiv_id}\t{paper.title}")


if __name__ == "__main__":
    main()
