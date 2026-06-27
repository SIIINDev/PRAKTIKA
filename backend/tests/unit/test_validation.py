"""Unit tests for upload validation helpers."""

import pytest

from app.services.validation import get_extension, validate_upload

MAX = 20 * 1024 * 1024
PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_get_extension():
    assert get_extension("report.PDF") == "pdf"
    assert get_extension("a.b.docx") == "docx"
    assert get_extension("noext") == ""


def test_valid_pdf():
    validate_upload("file.pdf", PDF_MIME, 1024, MAX)


def test_valid_docx():
    validate_upload("file.docx", DOCX_MIME, 1024, MAX)


def test_valid_with_generic_octet_stream():
    validate_upload("file.pdf", "application/octet-stream", 1024, MAX)


def test_rejects_bad_extension():
    with pytest.raises(ValueError):
        validate_upload("file.txt", "text/plain", 1024, MAX)


def test_rejects_bad_mime():
    with pytest.raises(ValueError):
        validate_upload("file.pdf", "image/png", 1024, MAX)


def test_rejects_empty_file():
    with pytest.raises(ValueError):
        validate_upload("file.pdf", PDF_MIME, 0, MAX)


def test_rejects_too_large():
    with pytest.raises(ValueError):
        validate_upload("file.pdf", PDF_MIME, MAX + 1, MAX)


def test_accepts_missing_content_type():
    validate_upload("file.docx", None, 1024, MAX)
