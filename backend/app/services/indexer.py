"""Background orchestration: extract -> chunk -> index, with status updates."""

import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.models.document import Document
from app.services import es_client
from app.services.chunker import chunk_text
from app.services.extractor import extract_text

logger = logging.getLogger(__name__)
_settings = get_settings()


async def _set_status(
    doc_id: str,
    *,
    status: str,
    chunk_count: int | None = None,
    error_message: str | None = None,
    indexed_at: datetime | None = None,
) -> None:
    """Persist an updated status (and related fields) for a document."""
    async with SessionLocal() as session:
        result = await session.execute(select(Document).where(Document.id == doc_id))
        document = result.scalar_one_or_none()
        if document is None:
            return
        document.status = status
        if chunk_count is not None:
            document.chunk_count = chunk_count
        document.error_message = error_message
        if indexed_at is not None:
            document.indexed_at = indexed_at
        await session.commit()


async def process_document(doc_id: str, path: str, file_name: str, content_type: str) -> None:
    """Run the full indexing pipeline for one document.

    Updates the document row to ``indexing`` then either ``done`` (with
    ``chunk_count`` and ``indexed_at``) or ``error`` (with ``error_message``).
    Never raises; failures are recorded on the row.
    """
    try:
        await _set_status(doc_id, status="indexing", error_message=None)
        pages = extract_text(path, content_type)
        chunks = chunk_text(pages, size=_settings.chunk_size, overlap=_settings.chunk_overlap)
        if not chunks:
            raise ValueError("Document produced no indexable chunks.")
        await es_client.ensure_index()
        count = await es_client.index_document(doc_id, file_name, chunks)
        await _set_status(
            doc_id,
            status="done",
            chunk_count=count,
            indexed_at=datetime.now(UTC),
            error_message=None,
        )
        logger.info("Indexed document %s (%d chunks)", doc_id, count)
    except Exception as exc:  # noqa: BLE001 - record any failure on the row
        logger.exception("Indexing failed for document %s", doc_id)
        await _set_status(doc_id, status="error", error_message=str(exc))
