"""Pydantic schemas for search and search history."""

from datetime import datetime

from pydantic import BaseModel


class SearchResult(BaseModel):
    """A single search hit mapped from an Elasticsearch document chunk."""

    chunk_id: str
    document_id: str
    file_name: str
    page: int
    text: str
    highlight: str
    score: float


class SearchOut(BaseModel):
    """Search response envelope matching the frontend contract."""

    query: str
    total: int
    page: int
    size: int
    took_ms: int
    cached: bool
    results: list[SearchResult]


class SearchHistoryItem(BaseModel):
    """A single recorded search query."""

    query: str
    results_count: int
    created_at: datetime


class SearchHistoryOut(BaseModel):
    """Recent search history, newest first."""

    history: list[SearchHistoryItem]
