from opensearchpy import OpenSearch
from src.config import get_settings
from src.services.opensearch.client import get_opensearch_client

INDEX_MAPPING = {
    "settings": {
        "analysis": {
            "analyzer": {
                "scientific_text": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "stop",          # removes "the", "a", "of", etc.
                        "porter_stem",   # optimize/optimization/optimizing -> optim
                    ],
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "arxiv_id": {"type": "keyword"},
            "title": {"type": "text", "analyzer": "scientific_text"},
            "abstract": {"type": "text", "analyzer": "scientific_text"},
            "authors": {"type": "keyword"},        # exact names, not tokenized
            "categories": {"type": "keyword"},     # exact match / filtering
            "published": {"type": "date"},
        }
    },
}


def ensure_index(client: OpenSearch | None = None) -> None:
    """Create the index if it doesn't already exist. Safe to call repeatedly."""
    client = client or get_opensearch_client()
    index_name = get_settings().opensearch.index

    if client.indices.exists(index=index_name):
        print(f"Index '{index_name}' already exists — skipping creation.")
        return

    client.indices.create(index=index_name, body=INDEX_MAPPING)
    print(f"Index '{index_name}' created.")