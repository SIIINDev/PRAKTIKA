"""Liveness/readiness health endpoint aggregating dependency status."""

from fastapi import APIRouter
from sqlalchemy import text

from app.core.db import engine
from app.schemas.health import HealthOut
from app.services import cache, es_client

router = APIRouter(tags=["health"])


async def _postgres_up() -> bool:
    """Return True if PostgreSQL answers a trivial query."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False


@router.get("/health", response_model=HealthOut)
async def health() -> HealthOut:
    """Report dependency readiness; HTTP 200 always, body reflects state."""
    es_up = await es_client.ping()
    redis_up = await cache.ping()
    pg_up = await _postgres_up()

    overall = "ok" if (es_up and redis_up and pg_up) else "degraded"
    return HealthOut(
        status=overall,
        elasticsearch="up" if es_up else "down",
        redis="up" if redis_up else "down",
        postgres="up" if pg_up else "down",
    )
