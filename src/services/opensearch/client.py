from opensearchpy import OpenSearch
from src.config import get_settings


def get_opensearch_client() -> OpenSearch:
    settings = get_settings()
    return OpenSearch(
        hosts=[settings.opensearch.host],
        http_compress=True,
        use_ssl=False,
        verify_certs=False,
    )