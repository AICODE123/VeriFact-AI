"""Unit tests for core/database.py, using temporary SQLite files."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from models.schemas import OfflineFact, VerdictLabel, VerificationResult


@pytest.fixture()
def temp_database(tmp_path):
    """Build a Database instance pointed at temp files instead of data/."""
    history_path = tmp_path / "history.db"
    kb_path = tmp_path / "offline_facts.db"

    fake_config = {
        "storage": {
            "history_db_path": str(history_path.relative_to(tmp_path)),
            "offline_kb_db_path": str(kb_path.relative_to(tmp_path)),
        },
        "ui": {"max_history_items": 50},
    }

    with patch("core.database.load_config", return_value=fake_config):
        with patch("core.database.get_project_root", return_value=tmp_path):
            from core.database import Database

            yield Database()


class TestHistory:
    def test_save_and_retrieve_result(self, temp_database):
        result = VerificationResult(
            claim="The sky is blue.",
            verdict=VerdictLabel.SUPPORTED,
            confidence=0.92,
            reason="Trusted sources confirm this.",
            evidence_chunks=[],
            sources=["https://britannica.com/sky"],
        )
        temp_database.save_result(result)

        history = temp_database.get_history()
        assert len(history) == 1
        assert history[0].claim == "The sky is blue."
        assert history[0].verdict == "Supported"

    def test_history_ordered_most_recent_first(self, temp_database):
        for claim in ["Claim A", "Claim B", "Claim C"]:
            temp_database.save_result(
                VerificationResult(
                    claim=claim,
                    verdict=VerdictLabel.INSUFFICIENT_EVIDENCE,
                    confidence=0.0,
                    reason="test",
                )
            )
        history = temp_database.get_history()
        assert [h.claim for h in history] == ["Claim C", "Claim B", "Claim A"]

    def test_clear_history(self, temp_database):
        temp_database.save_result(
            VerificationResult(claim="X", verdict=VerdictLabel.SUPPORTED, confidence=0.8, reason="test")
        )
        temp_database.clear_history()
        assert temp_database.get_history() == []


class TestOfflineKnowledgeBase:
    def test_seed_and_search(self, temp_database):
        facts = [
            OfflineFact(
                claim_text="The Eiffel Tower is located in Paris, France.",
                verdict=VerdictLabel.SUPPORTED,
                explanation="It stands in Paris.",
                source="Britannica",
                category="geography",
            )
        ]
        inserted = temp_database.seed_offline_kb(facts)
        assert inserted == 1
        assert temp_database.kb_fact_count() == 1

        match = temp_database.search_offline_kb("Eiffel Tower is in Berlin", ["Eiffel Tower"])
        assert match is not None
        assert match.verdict == VerdictLabel.SUPPORTED

    def test_search_no_match_returns_none(self, temp_database):
        result = temp_database.search_offline_kb("Some totally unrelated claim", ["nonexistent"])
        assert result is None

    def test_seed_ignores_duplicates_by_default(self, temp_database):
        fact = OfflineFact(
            claim_text="Water boils at 100 degrees Celsius.",
            verdict=VerdictLabel.SUPPORTED,
            explanation="Standard boiling point at sea level.",
            source="NASA",
            category="science",
        )
        temp_database.seed_offline_kb([fact])
        second_insert_count = temp_database.seed_offline_kb([fact])
        assert second_insert_count == 0
        assert temp_database.kb_fact_count() == 1
