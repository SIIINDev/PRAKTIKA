"""Tests for deep-pagination handling against Elasticsearch's max_result_window."""

import pytest

from app.services import es_client


class _FakeClient:
    """Minimal async ES stub recording whether search/count were called."""

    def __init__(self, total: int):
        self._total = total
        self.search_called = False

    async def count(self, index, body):  # noqa: ANN001, ARG002
        return {"count": self._total}

    async def search(self, index, body):  # noqa: ANN001, ARG002
        self.search_called = True
        return {
            "took": 1,
            "hits": {"total": {"value": self._total}, "hits": []},
        }


@pytest.mark.asyncio
async def test_deep_page_returns_empty_without_search(monkeypatch):
    """A page beyond max_result_window returns empty results, not an ES error."""
    fake = _FakeClient(total=42)
    monkeypatch.setattr(es_client, "get_client", lambda: fake)

    # page well past the window (from_ = (page-1)*size >= 10000)
    total, took_ms, hits = await es_client.search("query", page=2000, size=10)

    assert total == 42
    assert hits == []
    assert took_ms == 0
    assert fake.search_called is False  # short-circuited, never hit ES search


@pytest.mark.asyncio
async def test_boundary_page_shrinks_size(monkeypatch):
    """The page straddling the window edge still queries ES with a clamped size."""
    captured = {}

    class _CaptureClient(_FakeClient):
        async def search(self, index, body):  # noqa: ANN001, ARG002
            captured["from"] = body["from"]
            captured["size"] = body["size"]
            return await super().search(index, body)

    fake = _CaptureClient(total=10005)
    monkeypatch.setattr(es_client, "get_client", lambda: fake)

    # page 1112 * size 9 -> from_ = 9999; a full size of 9 would overflow the
    # 10000 window, so size must be clamped to 1.
    await es_client.search("query", page=1112, size=9)

    assert captured["from"] == 9999
    assert captured["size"] == es_client.MAX_RESULT_WINDOW - 9999  # == 1
