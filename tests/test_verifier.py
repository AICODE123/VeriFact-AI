"""Unit tests for core/verifier.py aggregation logic (mocked model)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from models.schemas import EvidenceChunk, NLILabel, NLIPrediction, VerdictLabel


def _make_verifier():
    """Construct a Verifier with the heavy model loading mocked out."""
    fake_tokenizer = MagicMock()
    fake_model = MagicMock()
    fake_model.config.id2label = {0: "contradiction", 1: "entailment", 2: "neutral"}

    with patch("core.verifier._load_nli_model", return_value=(fake_tokenizer, fake_model)):
        with patch("core.verifier.load_config") as mock_config:
            mock_config.return_value = {
                "models": {"nli_model": "fake-model", "nli_max_length": 128},
                "verification": {"min_confidence_threshold": 0.55, "min_evidence_chunks": 1},
            }
            from core.verifier import Verifier

            return Verifier()


def _prediction(label: NLILabel, entail: float, contra: float, neutral: float, similarity: float = 0.8) -> NLIPrediction:
    chunk = EvidenceChunk(text="evidence text", source_url="https://britannica.com/x", source_title="Britannica", similarity_score=similarity)
    return NLIPrediction(evidence=chunk, label=label, entailment_prob=entail, contradiction_prob=contra, neutral_prob=neutral)


class TestAggregate:
    def test_strong_support_yields_supported(self):
        verifier = _make_verifier()
        preds = [
            _prediction(NLILabel.ENTAILMENT, entail=0.95, contra=0.02, neutral=0.03),
            _prediction(NLILabel.ENTAILMENT, entail=0.90, contra=0.05, neutral=0.05),
        ]
        verdict, confidence = verifier.aggregate(preds)
        assert verdict == VerdictLabel.SUPPORTED
        assert confidence > 0.55

    def test_strong_contradiction_yields_contradicted(self):
        verifier = _make_verifier()
        preds = [
            _prediction(NLILabel.CONTRADICTION, entail=0.02, contra=0.95, neutral=0.03),
        ]
        verdict, confidence = verifier.aggregate(preds)
        assert verdict == VerdictLabel.CONTRADICTED
        assert confidence > 0.55

    def test_weak_mixed_signal_yields_insufficient(self):
        verifier = _make_verifier()
        preds = [
            _prediction(NLILabel.NEUTRAL, entail=0.48, contra=0.47, neutral=0.05),
        ]
        verdict, confidence = verifier.aggregate(preds)
        assert verdict == VerdictLabel.INSUFFICIENT_EVIDENCE

    def test_no_predictions_yields_insufficient(self):
        verifier = _make_verifier()
        verdict, confidence = verifier.aggregate([])
        assert verdict == VerdictLabel.INSUFFICIENT_EVIDENCE
        assert confidence == 0.0

    def test_higher_similarity_increases_weight(self):
        verifier = _make_verifier()
        low_sim = [_prediction(NLILabel.ENTAILMENT, entail=0.7, contra=0.2, neutral=0.1, similarity=0.1)]
        high_sim = [_prediction(NLILabel.ENTAILMENT, entail=0.7, contra=0.2, neutral=0.1, similarity=0.9)]
        _, conf_low = verifier.aggregate(low_sim)
        _, conf_high = verifier.aggregate(high_sim)
        assert conf_high >= conf_low
