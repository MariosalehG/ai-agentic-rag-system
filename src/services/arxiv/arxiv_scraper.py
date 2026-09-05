import logging
import re
import time
from datetime import UTC, datetime

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

# arXiv ids look like "2401.12345" or "2401.12345v2"; entry.id carries the version suffix.
_VERSION_SUFFIX_RE = re.compile(r"v\d+$")


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
    arxiv_id: str
    title: str
    pdf_url: str | None
    categories: list[str]
    authors: list[str]
    abstract: str
    published: datetime
    # Raw markdown from Docling, or None if there was no PDF link or parsing failed.
    parsed_content: str | None = None


class ArxivScraper:
    def __init__(self) -> None:
        self.converter = DocumentConverter()
        self._last_request_at: float | None = None

    def _throttle(self) -> None:
        """Block until ARXIV_MIN_REQUEST_INTERVAL_SECONDS has passed since the last request."""
        if self._last_request_at is not None:
            elapsed = time.monotonic() - self._last_request_at
            remaining = ARXIV_MIN_REQUEST_INTERVAL_SECONDS - elapsed
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

    def fetch_articles(self, search_query: str | None = None) -> list[ArxivArticle]:
        """Fetch articles from the arxiv export query and return them as ArxivArticle objects."""
        arxiv_query = f"{ARXIV_FEED}?{search_query}" if search_query else ARXIV_FEED

        resp = self._fetch(arxiv_query)
        feed = feedparser.parse(resp.content)

        articles = []
        for entry in feed.entries:
            pdf_link: str | None = None
            for link in entry.get("links", []):
                if link.get("title") == "pdf" or link.get("type") == "application/pdf":
                    pdf_link = link.get("href")
                    break

            arxiv_id = extract_arxiv_id(entry.id)

            parsed_content = None
            if pdf_link:
                try:
                    parsed_content = self.convert_to_markdown(pdf_link)
                except Exception:
                    logger.warning(
                        "Failed to parse PDF for %s: %s", arxiv_id, pdf_link, exc_info=True
                    )

            year, month, day, hour, minute, second = entry.published_parsed[:6]
            articles.append(
                ArxivArticle(
                    arxiv_id=arxiv_id,
                    title=entry.title,
                    pdf_url=pdf_link,
                    summary=entry.get("summary", ""),
                    published=datetime(year, month, day, hour, minute, second, tzinfo=UTC),
                    authors=[a.get("name", "") for a in entry.get("authors", [])],
                    categories=[t.get("term", "") for t in entry.get("tags", [])],
                    parsed_content=parsed_content,
                )
            )

        articles.sort(key=lambda a: a.published, reverse=True)

        return articles

    def convert_to_markdown(self, pdf_url: str) -> str:
        """Convert a PDF from the given URL to markdown text using the DocumentConverter."""
        result = self.converter.convert(pdf_url)
        doc = result.document

        if doc is None:
            raise ValueError(f"Failed to convert PDF from {pdf_url} to text.")

        return doc.export_to_markdown()

def extract_arxiv_id(id: str) -> str | None:
    """Extract the arXiv ID from a URL, or return None if it can't be found."""
    return _VERSION_SUFFIX_RE.sub("", id.rsplit("/", 1)[-1]) or None


if __name__ == "__main__":
    scraper = ArxivScraper()
    articles = scraper.fetch_articles(
        search_query="search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=5"
    )
    print(f"Here is the number fetched articles from the arxiv feed: {len(articles)}")
