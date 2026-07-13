"""
Unit tests for core/claim_processor.py.

These tests exercise the static/pure-logic helpers (`_build_search_query`,
`_unique`) directly rather than loading the actual spaCy model, keeping the
test suite fast and independent of large model downloads. A separate
integration-style test (marked accordingly) covers the full `process()`
call for environments where the spaCy model is installed.
"""

from __future__ import annotations

import pytest

from core.claim_processor import ClaimProcessor, ClaimProcessorError


class TestBuildSearchQuery:
    def test_prioritizes_location_entities(self):
        query = ClaimProcessor._build_search_query(
            claim="The Eiffel Tower is located in Berlin.",
            organizations=[],
            locations=["Berlin"],
            dates=[],
            generic_entities=[],
            key_nouns=["Tower"],
        )
        assert "Berlin" in query
        assert "location" in query

    def test_falls_back_to_key_nouns_when_no_entities(self):
        query = ClaimProcessor._build_search_query(
            claim="The sky is blue.",
            organizations=[],
            locations=[],
            dates=[],
            generic_entities=[],
            key_nouns=["sky"],
        )
        assert "sky" in query

    def test_falls_back_to_raw_claim_when_nothing_extracted(self):
        claim = "This is vague."
        query = ClaimProcessor._build_search_query(
            claim=claim, organizations=[], locations=[], dates=[], generic_entities=[], key_nouns=[]
        )
        assert query == claim

    def test_organization_anchor(self):
        query = ClaimProcessor._build_search_query(
            claim="NASA was founded in 1958.",
            organizations=["NASA"],
            locations=[],
            dates=["1958"],
            generic_entities=[],
            key_nouns=[],
        )
        # dates present -> anchor should be "date facts" per priority order
        assert "NASA" in query


class TestUnique:
    def test_deduplicates_case_insensitively(self):
        result = ClaimProcessor._unique(["Paris", "paris", "Berlin", " Paris "])
        assert result == ["Paris", "Berlin"]

    def test_filters_empty_strings(self):
        result = ClaimProcessor._unique(["", "  ", "Tokyo"])
        assert result == ["Tokyo"]

    def test_empty_list(self):
        assert ClaimProcessor._unique([]) == []


@pytest.mark.integration
class TestClaimProcessorIntegration:
    """Requires the spaCy model (en_core_web_sm) to be installed."""

    def test_process_extracts_location(self):
        processor = ClaimProcessor()
        result = processor.process("The Eiffel Tower is located in Berlin.")
        assert result.original_claim == "The Eiffel Tower is located in Berlin."
        assert any("Berlin" in loc for loc in result.locations)
        assert result.search_query

    def test_empty_claim_raises(self):
        processor = ClaimProcessor()
        with pytest.raises(ClaimProcessorError):
            processor.process("   ")
