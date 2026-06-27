"""Pure text chunking utilities (sliding window with overlap)."""

from typing import TypedDict


class Chunk(TypedDict):
    """A single chunk of text with its position metadata."""

    chunk_index: int
    page_number: int
    text: str


def chunk_text(
    pages: list[tuple[int, str]],
    size: int = 1000,
    overlap: int = 100,
) -> list[Chunk]:
    """Split per-page text into overlapping fixed-size chunks.

    Args:
        pages: Sequence of ``(page_number, text)`` pairs.
        size: Maximum chunk length in characters (must be > 0).
        overlap: Number of characters shared between consecutive chunks of the
            same page (must be >= 0 and < ``size``).

    Returns:
        A flat list of chunks ordered by page then position, each carrying a
        globally increasing ``chunk_index`` and its source ``page_number``.

    Raises:
        ValueError: If ``size`` or ``overlap`` are out of range.
    """
    if size <= 0:
        raise ValueError("size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be >= 0 and < size")

    step = size - overlap
    chunks: list[Chunk] = []
    chunk_index = 0

    for page_number, raw_text in pages:
        text = (raw_text or "").strip()
        if not text:
            continue
        start = 0
        length = len(text)
        while start < length:
            piece = text[start : start + size].strip()
            if piece:
                chunks.append(
                    Chunk(
                        chunk_index=chunk_index,
                        page_number=page_number,
                        text=piece,
                    )
                )
                chunk_index += 1
            start += step

    return chunks
