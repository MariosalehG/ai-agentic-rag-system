from src.services.arxiv.arxiv_scraper import extract_arxiv_id, ArxivScraper
from unittest.mock import patch, Mock

ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2401.00001v1</id>
    <title>A Test Paper</title>
    <summary>An abstract.</summary>
    <published>2024-01-01T00:00:00Z</published>
    <author><name>Jane Doe</name></author>
    <category term="cs.AI"/>
    <link title="pdf" href="http://arxiv.org/pdf/2401.00001v1"/>
  </entry>
</feed>
"""

def test_extract_arxiv_id():
    id = "2401.00001v1"
    assert extract_arxiv_id(id) == "2401.00001"  # or without version — decide the 

@patch("src.services.arxiv.arxiv_scraper.requests.get")
def test_fetch_articles(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = ATOM_FEED.encode("utf-8")
    mock_response.raise_for_status = Mock()  # no-op, simulates HTTP 200
    mock_get.return_value = mock_response

    scraper = ArxivScraper.__new__(ArxivScraper)  # skip DocumentConverter() in __init__
    scraper._last_request_at = None

    with patch.object(scraper, "convert_to_markdown", return_value="parsed md"): # Mocks convert_to_markdown to return "parsed md" when called
        articles = scraper.fetch_articles()

    assert len(articles) == 1
    assert articles[0].arxiv_id == "2401.00001"
    assert articles[0].parsed_content == "parsed md"
    mock_get.assert_called_once()