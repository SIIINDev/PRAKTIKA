"""FastAPI application factory and lifecycle wiring."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api import documents, health, search
from app.core.config import get_settings
from app.core.db import init_db
from app.services import cache, es_client

_settings = get_settings()

logging.basicConfig(level=_settings.log_level.upper())
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise dependencies on startup; degrade gracefully if unavailable."""
    try:
        await init_db()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Database init failed at startup: %s", exc)

    try:
        await es_client.ensure_index()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Elasticsearch index init failed at startup: %s", exc)

    try:
        await cache.ping()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis ping failed at startup: %s", exc)

    yield

    await es_client.close_client()
    await cache.close_client()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="Knowledge Base Search API",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(documents.router, prefix="/api/v1")
    app.include_router(search.router, prefix="/api/v1")
    app.include_router(health.router)

    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    return app


app = create_app()
