from opensearchpy import OpenSearch
from src.config import get_settings
from src.services.opensearch.client import get_opensearch_client

INDEX_MAPPING = {
    "settings": {
        "index":{
            "knn": True,  # enable kNN for vector search
        },
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
            
            # NEW - chunk level-fields
            "chunk_text": {"type": "text", "analyzer": "scientific_text"},
            "section_title": {"type": "keyword"},
            "chunk_index": {"type": "integer"},
            "embedding": {
                "type": "knn_vector",
                "dimension": 1024,  # must match jina-embeddings-v3 exactly
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "lucene",
                },
            },
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

def recreate_index(client: OpenSearch | None = None) -> None:
    """Delete and recreate the index. Destroys all indexed data.

    Required when changing immutable settings (like enabling knn) or field
    mappings. Safe because Postgres is the source of truth — you can always
    re-index from there.
    """
    client = client or get_opensearch_client()
    index_name = get_settings().opensearch.index

    if client.indices.exists(index=index_name):
        client.indices.delete(index=index_name)
        print(f"Deleted index '{index_name}'")

    client.indices.create(index=index_name, body=INDEX_MAPPING)
    print(f"Created index '{index_name}' with knn enabled")