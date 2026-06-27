"""Unit tests for the pure text chunker."""

import pytest

from app.services.chunker import chunk_text


def test_short_text_single_chunk():
    chunks = chunk_text([(1, "hello world")], size=1000, overlap=100)
    assert len(chunks) == 1
    assert chunks[0]["text"] == "hello world"
    assert chunks[0]["page_number"] == 1
    assert chunks[0]["chunk_index"] == 0


def test_empty_text_yields_no_chunks():
    assert chunk_text([(1, "")], size=1000, overlap=100) == []
    assert chunk_text([(1, "   ")], size=1000, overlap=100) == []


def test_chunk_sizes_respect_window():
    text = "a" * 2500
    chunks = chunk_text([(1, text)], size=1000, overlap=100)
    for chunk in chunks:
        assert len(chunk["text"]) <= 1000


def test_overlap_correctness():
    text = "".join(str(i % 10) for i in range(2000))
    chunks = chunk_text([(1, text)], size=1000, overlap=100)
    # step = 900, so second chunk starts at index 900
    assert chunks[0]["text"] == text[0:1000]
    assert chunks[1]["text"] == text[900:1900]
    # overlapping region must match
    assert chunks[0]["text"][-100:] == chunks[1]["text"][:100]


def test_chunk_index_is_monotonic_and_global():
    pages = [(1, "x" * 1500), (2, "y" * 1500)]
    chunks = chunk_text(pages, size=1000, overlap=100)
    indices = [c["chunk_index"] for c in chunks]
    assert indices == sorted(indices)
    assert indices == list(range(len(chunks)))


def test_multi_page_page_number_preserved():
    pages = [(1, "alpha"), (5, "beta"), (9, "gamma")]
    chunks = chunk_text(pages, size=1000, overlap=100)
    assert [c["page_number"] for c in chunks] == [1, 5, 9]


def test_invalid_size_raises():
    with pytest.raises(ValueError):
        chunk_text([(1, "x")], size=0, overlap=0)


def test_invalid_overlap_raises():
    with pytest.raises(ValueError):
        chunk_text([(1, "x")], size=100, overlap=100)
    with pytest.raises(ValueError):
        chunk_text([(1, "x")], size=100, overlap=-1)
