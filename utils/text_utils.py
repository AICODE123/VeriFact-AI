"""
text_utils.py
=============
Small, dependency-light text helpers shared by multiple core modules
(cleaning scraped HTML text, splitting text into overlapping word chunks).
"""

from __future__ import annotations

import re
from typing import List


def clean_text(raw_text: str) -> str:
    """
    Normalize whitespace and strip boilerplate artifacts from scraped text.

    Args:
        raw_text: Raw text extracted from a webpage.

    Returns:
        Cleaned, single-spaced text.
    """
    if not raw_text:
        return ""

    text = re.sub(r"\s+", " ", raw_text)
    text = re.sub(r"\[\d+\]", "", text)  # strip Wikipedia-style [1] citations
    return text.strip()


def chunk_text(
    text: str,
    chunk_size_words: int = 120,
    overlap_words: int = 20,
    min_chunk_words: int = 15,
) -> List[str]:
    """
    Split text into overlapping, word-bounded chunks suitable for embedding.

    Overlap helps avoid losing context that straddles a chunk boundary.

    Args:
        text: Cleaned input text.
        chunk_size_words: Target number of words per chunk.
        overlap_words: Number of words shared between consecutive chunks.
        min_chunk_words: Chunks shorter than this are discarded (usually
            trailing fragments).

    Returns:
        List of text chunks.
    """
    words = text.split()
    if not words:
        return []

    if chunk_size_words <= overlap_words:
        raise ValueError("chunk_size_words must be greater than overlap_words")

    chunks: List[str] = []
    step = chunk_size_words - overlap_words
    for start in range(0, len(words), step):
        window = words[start : start + chunk_size_words]
        if len(window) < min_chunk_words:
            continue
        chunks.append(" ".join(window))
        if start + chunk_size_words >= len(words):
            break

    return chunks


def truncate(text: str, max_chars: int = 300) -> str:
    """Truncate text to `max_chars`, adding an ellipsis if shortened."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"
