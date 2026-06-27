"""Async Elasticsearch client wrapper for the documents index."""

import logging
from datetime import UTC, datetime

from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk

from app.core.config import get_settings
from app.services.chunker import Chunk

logger = logging.getLogger(__name__)

_settings = get_settings()
_client: AsyncElasticsearch | None = None

INDEX_SETTINGS = {
    "settings": {
        "analysis": {
            "analyzer": {
                "russian_custom": {
                    "type": "russian",
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "chunk_id": {"type": "keyword"},
            "document_id": {"type": "keyword"},
            "file_name": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 512}},
            },
            "page_number": {"type": "integer"},
            "chunk_index": {"type": "integer"},
            "text": {"type": "text", "analyzer": "russian_custom"},
            "created_at": {"type": "date"},
        }
    },
}


def get_client() -> AsyncElasticsearch:
    """Return a lazily created singleton Elasticsearch client."""
    global _client
    if _client is None:
        _client = AsyncElasticsearch(_settings.elasticsearch_url, request_timeout=30)
    return _client


async def close_client() -> None:
    """Close the Elasticsearch client if it was created."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None


async def ping() -> bool:
    """Return True if Elasticsearch responds to a ping."""
    try:
        return bool(await get_client().ping())
    except Exception:  # noqa: BLE001
        return False


async def ensure_index() -> None:
    """Create the documents index with the russian analyzer if it is missing."""
    client = get_client()
    exists = await client.indices.exists(index=_settings.elasticsearch_index)
    if not exists:
        await client.indices.create(index=_settings.elasticsearch_index, body=INDEX_SETTINGS)
        logger.info("Created Elasticsearch index '%s'", _settings.elasticsearch_index)


async def index_document(doc_id: str, file_name: str, chunks: list[Chunk]) -> int:
    """Bulk-index the chunks of a document.

    Args:
        doc_id: Owning document UUID.
        file_name: Original file name (indexed for search and display).
        chunks: Chunks produced by :func:`app.services.chunker.chunk_text`.

    Returns:
        The number of chunks indexed.
    """
    client = get_client()
    now = datetime.now(UTC).isoformat()
    actions = [
        {
            "_index": _settings.elasticsearch_index,
            "_id": f"{doc_id}:{chunk['chunk_index']}",
            "_source": {
                "chunk_id": f"{doc_id}:{chunk['chunk_index']}",
                "document_id": doc_id,
                "file_name": file_name,
                "page_number": chunk["page_number"],
                "chunk_index": chunk["chunk_index"],
                "text": chunk["text"],
                "created_at": now,
            },
        }
        for chunk in chunks
    ]
    if not actions:
        return 0
    await async_bulk(client, actions, refresh="wait_for")
    return len(actions)


async def search(q: str, page: int, size: int) -> tuple[int, int, list[dict]]:
    """Run a highlighted multi_match search over the documents index.

    Args:
        q: Non-empty query string.
        page: 1-based page number.
        size: Page size.

    Returns:
        A tuple ``(total, took_ms, hits)`` where ``hits`` is a list of dicts
        with keys ``chunk_id, document_id, file_name, page, text, highlight,
        score``.
    """
    client = get_client()
    from_ = (page - 1) * size
    body = {
        "from": from_,
        "size": size,
        "query": {
            "multi_match": {
                "query": q,
                "fields": ["text", "file_name"],
            }
        },
        "highlight": {
            "pre_tags": ["<em>"],
            "post_tags": ["</em>"],
            "fragment_size": 150,
            "number_of_fragments": 1,
            "fields": {"text": {}},
        },
    }
    response = await client.search(index=_settings.elasticsearch_index, body=body)

    took_ms = int(response.get("took", 0))
    total = int(response["hits"]["total"]["value"])
    hits: list[dict] = []
    for hit in response["hits"]["hits"]:
        source = hit["_source"]
        highlight_fragments = hit.get("highlight", {}).get("text", [])
        highlight = highlight_fragments[0] if highlight_fragments else source.get("text", "")[:150]
        hits.append(
            {
                "chunk_id": source["chunk_id"],
                "document_id": source["document_id"],
                "file_name": source["file_name"],
                "page": source.get("page_number", 1),
                "text": source.get("text", ""),
                "highlight": highlight,
                "score": float(hit.get("_score") or 0.0),
            }
        )
    return total, took_ms, hits


async def delete_document(doc_id: str) -> None:
    """Delete every chunk belonging to a document by ``document_id``."""
    client = get_client()
    await client.delete_by_query(
        index=_settings.elasticsearch_index,
        body={"query": {"term": {"document_id": doc_id}}},
        refresh=True,
        ignore_unavailable=True,
        conflicts="proceed",
    )
