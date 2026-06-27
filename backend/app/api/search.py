"""Full-text search and search history endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.core.metrics import SEARCH_LATENCY, SEARCH_REQUESTS
from app.models.document import SearchHistory
from app.schemas.search import (
    SearchHistoryItem,
    SearchHistoryOut,
    SearchOut,
    SearchResult,
)
from app.services import cache, es_client

logger = logging.getLogger(__name__)
router = APIRouter(tags=["search"])
_settings = get_settings()


@router.get("/search", response_model=SearchOut)
async def search(
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> SearchOut:
    """Search indexed chunks, with Redis caching and history recording."""
    query = q.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'q' must not be empty",
        )

    with SEARCH_LATENCY.time():
        cache_key = f"search:{query}:{page}:{size}"
        cached_payload = await cache.get_json(cache_key)
        if cached_payload is not None:
            SEARCH_REQUESTS.labels(cached="true").inc()
            cached_payload["cached"] = True
            return SearchOut(**cached_payload)

        try:
            total, took_ms, hits = await es_client.search(query, page, size)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Search failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search backend unavailable",
            ) from exc

        results = [SearchResult(**hit) for hit in hits]
        response = SearchOut(
            query=query,
            total=total,
            page=page,
            size=size,
            took_ms=took_ms,
            cached=False,
            results=results,
        )

        await cache.set_json(cache_key, response.model_dump(), _settings.search_cache_ttl)
        session.add(SearchHistory(query=query, results_count=total))
        await session.commit()
        SEARCH_REQUESTS.labels(cached="false").inc()

    return response


@router.get("/search/history", response_model=SearchHistoryOut)
async def search_history(session: AsyncSession = Depends(get_session)) -> SearchHistoryOut:
    """Return the most recent search queries, newest first."""
    result = await session.execute(
        select(SearchHistory).order_by(SearchHistory.created_at.desc()).limit(20)
    )
    rows = result.scalars().all()

    seen: set[str] = set()
    items: list[SearchHistoryItem] = []
    for row in rows:
        if row.query in seen:
            continue
        seen.add(row.query)
        items.append(
            SearchHistoryItem(
                query=row.query,
                results_count=row.results_count,
                created_at=row.created_at,
            )
        )
    return SearchHistoryOut(history=items)
