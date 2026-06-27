"""Unit tests for the text extractor (DOCX built in-memory, dispatch, errors)."""

import os

import pytest

from app.services.extractor import extract_text


def test_unsupported_type_raises(tmp_path):
    path = tmp_path / "file.txt"
    path.write_text("hello")
    with pytest.raises(ValueError):
        extract_text(str(path), "text/plain")


def test_missing_file_raises():
    with pytest.raises(ValueError):
        extract_text("/nonexistent/path/file.pdf", "application/pdf")


def test_empty_file_raises(tmp_path):
    path = tmp_path / "file.pdf"
    path.write_bytes(b"")
    with pytest.raises(ValueError):
        extract_text(str(path), "application/pdf")


def test_docx_extraction(tmp_path):
    docx = pytest.importorskip("docx")
    document = docx.Document()
    document.add_paragraph("Привет мир")
    document.add_paragraph("Second line of text")
    out_path = os.path.join(tmp_path, "doc.docx")
    document.save(out_path)

    pages = extract_text(
        out_path,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert len(pages) == 1
    assert pages[0][0] == 1
    assert "Привет мир" in pages[0][1]
    assert "Second line of text" in pages[0][1]


def test_docx_empty_raises(tmp_path):
    docx = pytest.importorskip("docx")
    document = docx.Document()
    out_path = os.path.join(tmp_path, "empty.docx")
    document.save(out_path)
    with pytest.raises(ValueError):
        extract_text(out_path, None)
