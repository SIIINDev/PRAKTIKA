"""Pydantic schemas for document resources."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    """Full document representation returned by list/detail endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    file_name: str
    content_type: str
    size_bytes: int
    status: str
    chunk_count: int
    error_message: str | None
    uploaded_at: datetime
    indexed_at: datetime | None


class DocumentUploadOut(BaseModel):
    """Minimal acknowledgement returned right after an upload is accepted."""

    id: str
    file_name: str
    status: str


class DocumentListOut(BaseModel):
    """Paginated-free listing of documents, newest first."""

    documents: list[DocumentOut]
    total: int
