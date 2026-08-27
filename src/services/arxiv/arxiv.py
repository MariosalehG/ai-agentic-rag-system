import json
import logging
import time
from datetime import datetime, timezone

import feedparser
import requests
from docling.document_converter import DocumentConverter
from pydantic import BaseModel
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from src.config import get_settings

logger = logging.getLogger(__name__)

ARXIV_FEED = get_settings().arxiv__feed or "https://export.arxiv.org/api/query"

# arXiv's API usage policy asks for no more than one request every 3 seconds.
ARXIV_MIN_REQUEST_INTERVAL_SECONDS = 3.0


def _is_transient_error(exc: BaseException) -> bool:
    """True for errors worth retrying: network hiccups, rate limiting, server-side failures.

    A 400 means the query itself is malformed - retrying sends the exact same bad
    request and gets the exact same 400 every time, so we let it raise immediately
    instead of burning the retry budget (and 3s+ of backoff) on something that will
    never succeed. A timeout or a 5xx, by contrast, says nothing about whether the
    request was valid - it may well succeed if we just try again.
    """
    if isinstance(exc, requests.exceptions.RequestException):
        status = exc.response.status_code if exc.response is not None else None
        return status == 429 or (status is not None and status >= 500)
    return isinstance(exc, (requests.exceptions.ConnectionError, requests.exceptions.Timeout))


class ArxivArticle(BaseModel):
    title: str
    pdf_url: str | None
    categories: str
    authors: str
    summary: str
    published: datetime
    arxiv_id: str
    parsed_content: json


class ArxivScraper:
    def __init__(self):
        self.converter = DocumentConverter()
        self._last_request_at: float | None = None

    def _throttle(self) -> None:
        """Block until at least ARXIV_MIN_REQUEST_INTERVAL_SECONDS has passed since the last request."""
        if self._last_request_at is not None:
            remaining = ARXIV_MIN_REQUEST_INTERVAL_SECONDS - (time.monotonic() - self._last_request_at)
            if remaining > 0:
                time.sleep(remaining)
        self._last_request_at = time.monotonic()

    @retry(
        retry=retry_if_exception(_is_transient_error),
        wait=wait_exponential_jitter(initial=ARXIV_MIN_REQUEST_INTERVAL_SECONDS, max=30),
        stop=stop_after_attempt(5),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _fetch(self, url: str) -> requests.Response:
        self._throttle()
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp

    def fetch_articles(self, searchQuery : str | None = None) -> list[ArxivArticle]:
        """Fetch articles from the arxiv export query and return them as a list of ArxivArticle objects."""
        articles = []

        arxiv_query = f"{ARXIV_FEED}?{searchQuery}" if searchQuery else ARXIV_FEED

        resp = self._fetch(arxiv_query)
        feed = feedparser.parse(resp.content)
        for entry in feed.entries:
            pdf_link : str | None = None
            for link in entry.get("links", []):
                if link.get("type") == "PDF":
                    pdf_link = link.get("href")
                    break
            
            articles.append(
                ArxivArticle(
                    title=entry.title,
                    pdf_url=pdf_link,
                    summary=entry.get("summary", ""),
                    published=datetime(*entry.published_parsed[:6], tzinfo=timezone.utc),
                    authors=json.dumps(entry.get("authors", {})),
                    categories=json.dumps(entry.get("tags", {})),
                    arxiv_id=entry.id.rsplit("/", 1)[-1],
                    parsed_content=convert_to_markdown(self=self,pdf_url=pdf_link) if pdf_link else None
                )
            )

        articles.sort(key=lambda a: a.published, reverse=True)

        return articles

    def convert_to_markdown(self, pdf_url: str) -> str:
        """Convert a PDF from the given URL to text using the DocumentConverter."""
        result = self.converter.convert_pdf_from_url(pdf_url)
        doc = result.document

        if doc is None:
            raise ValueError(f"Failed to convert PDF from {pdf_url} to text.")

        return doc.export_to_markdown()

        
        


if __name__ == "__main__":
    scraper = ArxivScraper()
    articles = scraper.fetch_articles(searchQuery="search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&limit=5")
    print(f"Here are the fetched articles from the arxiv feed: {articles}")
