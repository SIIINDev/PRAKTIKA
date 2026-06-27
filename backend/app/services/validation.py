"""Pure upload-validation helpers (testable without HTTP)."""

ALLOWED_EXTENSIONS: set[str] = {"pdf", "docx"}

ALLOWED_MIME_TYPES: set[str] = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    # Some clients send a generic type; the extension check still guards us.
    "application/octet-stream",
}

EXTENSION_BY_MIME: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}


def get_extension(file_name: str) -> str:
    """Return the lowercased extension of ``file_name`` without the dot."""
    if "." not in file_name:
        return ""
    return file_name.rsplit(".", 1)[-1].lower()


def validate_upload(
    file_name: str,
    content_type: str | None,
    size_bytes: int,
    max_bytes: int,
) -> None:
    """Validate an upload's extension, MIME type and size.

    Args:
        file_name: Original client file name.
        content_type: Reported MIME type (may be ``None``).
        size_bytes: Size of the uploaded payload in bytes.
        max_bytes: Maximum allowed size in bytes.

    Raises:
        ValueError: With a human-readable message when validation fails. The
            caller maps this to an HTTP 400 response.
    """
    extension = get_extension(file_name)
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file extension '.{extension}'. Allowed: "
            f"{', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )

    mime = (content_type or "").lower().split(";", 1)[0].strip()
    if mime and mime not in ALLOWED_MIME_TYPES:
        raise ValueError(f"Unsupported content type '{mime}'.")

    if size_bytes <= 0:
        raise ValueError("Uploaded file is empty.")

    if size_bytes > max_bytes:
        max_mb = max_bytes / (1024 * 1024)
        raise ValueError(f"File too large. Maximum allowed size is {max_mb:.0f} MB.")
