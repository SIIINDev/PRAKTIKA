"""Offline API tests for /health and upload validation using ASGITransport.

These tests stub out Elasticsearch, Redis and PostgreSQL so the suite runs
without any live services.
"""

import io

import pytest
from httpx import ASGITransport, AsyncClient

from app.api import health as health_api
from app.core import db as core_db
from app.main import create_app
from app.services import cache, es_client


@pytest.fixture
def app(monkeypatch):
    """Build the app with all external dependencies stubbed."""

    async def fake_init_db():
        return None

    async def fake_ensure_index():
        return None

    async def fake_es_ping():
        return False

    async def fake_redis_ping():
        return False

    async def fake_pg_up():
        return False

    monkeypatch.setattr(core_db, "init_db", fake_init_db)
    monkeypatch.setattr(es_client, "ensure_index", fake_ensure_index)
    monkeypatch.setattr(es_client, "ping", fake_es_ping)
    monkeypatch.setattr(cache, "ping", fake_redis_ping)
    monkeypatch.setattr(health_api, "_postgres_up", fake_pg_up)
    # Avoid touching es_client.ping reference captured in health module namespace.
    monkeypatch.setattr(health_api.es_client, "ping", fake_es_ping)
    monkeypatch.setattr(health_api.cache, "ping", fake_redis_ping)

    application = create_app()

    async def fake_get_session():
        yield None

    application.dependency_overrides[core_db.get_session] = fake_get_session
    return application


async def test_health_degraded_when_deps_down(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["elasticsearch"] == "down"
    assert body["redis"] == "down"
    assert body["postgres"] == "down"


async def test_upload_rejects_bad_extension(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("note.txt", io.BytesIO(b"hello"), "text/plain")}
        resp = await client.post("/api/v1/documents/upload", files=files)

    assert resp.status_code == 400
    assert "detail" in resp.json()


async def test_search_requires_non_empty_query(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/search", params={"q": "   "})
    assert resp.status_code == 400
