"""Document upload, listing, retrieval and deletion endpoints."""

import logging
import os
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.models.document import Document
from app.schemas.document import DocumentListOut, DocumentOut, DocumentUploadOut
from app.services import es_client
from app.services.indexer import process_document
from app.services.validation import validate_upload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])
_settings = get_settings()


@router.post(
    "/upload",
    response_model=DocumentUploadOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> DocumentUploadOut:
    """Accept a PDF/DOCX upload, persist it and schedule background indexing."""
    payload = await file.read()
    file_name = file.filename or "upload"

    try:
        validate_upload(file_name, file.content_type, len(payload), _settings.max_upload_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    doc_id = str(uuid.uuid4())
    os.makedirs(_settings.upload_dir, exist_ok=True)
    extension = file_name.rsplit(".", 1)[-1].lower()
    stored_path = os.path.join(_settings.upload_dir, f"{doc_id}.{extension}")
    with open(stored_path, "wb") as fh:
        fh.write(payload)

    document = Document(
        id=doc_id,
        file_name=file_name,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(payload),
        status="uploading",
        chunk_count=0,
        stored_path=stored_path,
    )
    session.add(document)
    await session.commit()

    background_tasks.add_task(
        process_document,
        doc_id,
        stored_path,
        file_name,
        document.content_type,
    )

    return DocumentUploadOut(id=doc_id, file_name=file_name, status="uploading")


@router.get("", response_model=DocumentListOut)
async def list_documents(session: AsyncSession = Depends(get_session)) -> DocumentListOut:
    """Return all documents, newest first, with a total count."""
    result = await session.execute(select(Document).order_by(Document.uploaded_at.desc()))
    documents = result.scalars().all()
    return DocumentListOut(
        documents=[DocumentOut.model_validate(d) for d in documents],
        total=len(documents),
    )


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: str,
    session: AsyncSession = Depends(get_session),
) -> DocumentOut:
    """Return a single document by id, or 404 if it does not exist."""
    result = await session.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentOut.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a document row, its stored file and all of its ES chunks."""
    result = await session.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    try:
        await es_client.delete_document(document_id)
    except Exception as exc:  # noqa: BLE001 - ES failure must not block row deletion
        logger.warning("Failed to delete ES chunks for %s: %s", document_id, exc)

    if document.stored_path and os.path.exists(document.stored_path):
        try:
            os.remove(document.stored_path)
        except OSError as exc:
            logger.warning("Failed to remove file %s: %s", document.stored_path, exc)

    await session.delete(document)
    await session.commit()
