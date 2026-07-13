"""Unit tests for utils/text_utils.py."""

from __future__ import annotations

import pytest

from utils.text_utils import chunk_text, clean_text, truncate


class TestCleanText:
    def test_collapses_whitespace(self):
        assert clean_text("Hello    world\n\n  foo") == "Hello world foo"

    def test_strips_citation_markers(self):
        assert clean_text("Paris is the capital.[1] It is in France.[23]") == "Paris is the capital. It is in France."

    def test_empty_input_returns_empty(self):
        assert clean_text("") == ""
        assert clean_text(None) == ""


class TestChunkText:
    def test_basic_chunking(self):
        text = " ".join(f"word{i}" for i in range(300))
        chunks = chunk_text(text, chunk_size_words=100, overlap_words=20, min_chunk_words=10)
        assert len(chunks) >= 3
        for chunk in chunks:
            assert len(chunk.split()) <= 100

    def test_short_text_single_chunk(self):
        text = "This is a short sentence with enough words to pass the minimum."
        chunks = chunk_text(text, chunk_size_words=120, overlap_words=20, min_chunk_words=5)
        assert len(chunks) == 1

    def test_empty_text_returns_no_chunks(self):
        assert chunk_text("", chunk_size_words=100, overlap_words=10) == []

    def test_fragment_below_min_words_dropped(self):
        text = "one two three"
        chunks = chunk_text(text, chunk_size_words=100, overlap_words=10, min_chunk_words=10)
        assert chunks == []

    def test_invalid_overlap_raises(self):
        with pytest.raises(ValueError):
            chunk_text("some text here", chunk_size_words=10, overlap_words=10)


class TestTruncate:
    def test_no_truncation_needed(self):
        assert truncate("short text", max_chars=50) == "short text"

    def test_truncates_and_adds_ellipsis(self):
        result = truncate("a" * 100, max_chars=20)
        assert len(result) == 20
        assert result.endswith("…")
