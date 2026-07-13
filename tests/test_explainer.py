"""Unit tests for core/explainer.py."""

from __future__ import annotations

from core.explainer import Explainer
from models.schemas import EvidenceChunk, NLILabel, NLIPrediction, VerdictLabel


def _prediction(label, entail, contra, neutral, text="Evidence snippet text.", url="https://britannica.com/x", title="Britannica"):
    chunk = EvidenceChunk(text=text, source_url=url, source_title=title, similarity_score=0.8)
    return NLIPrediction(evidence=chunk, label=label, entailment_prob=entail, contradiction_prob=contra, neutral_prob=neutral)


class TestBuildResult:
    def test_supported_result_has_reason_and_sources(self):
        explainer = Explainer()
        preds = [_prediction(NLILabel.ENTAILMENT, 0.9, 0.05, 0.05)]
        result = explainer.build_result("The Eiffel Tower is in Paris.", VerdictLabel.SUPPORTED, 0.9, preds)

        assert result.verdict == VerdictLabel.SUPPORTED
        assert "Paris" in result.reason or "Eiffel" in result.reason
        assert result.sources == ["https://britannica.com/x"]
        assert result.confidence_percent() == "90%"

    def test_contradicted_result_mentions_contradiction(self):
        explainer = Explainer()
        preds = [_prediction(NLILabel.CONTRADICTION, 0.05, 0.9, 0.05)]
        result = explainer.build_result("The Eiffel Tower is in Berlin.", VerdictLabel.CONTRADICTED, 0.9, preds)

        assert result.verdict == VerdictLabel.CONTRADICTED
        assert "contradict" in result.reason.lower()

    def test_insufficient_evidence_with_no_predictions(self):
        explainer = Explainer()
        result = explainer.build_result("Some vague claim.", VerdictLabel.INSUFFICIENT_EVIDENCE, 0.0, [])

        assert result.verdict == VerdictLabel.INSUFFICIENT_EVIDENCE
        assert result.evidence_chunks == []
        assert result.sources == []

    def test_deduplicates_sources(self):
        explainer = Explainer()
        preds = [
            _prediction(NLILabel.ENTAILMENT, 0.9, 0.05, 0.05, url="https://britannica.com/x"),
            _prediction(NLILabel.ENTAILMENT, 0.85, 0.05, 0.1, url="https://britannica.com/x"),
        ]
        result = explainer.build_result("Test claim.", VerdictLabel.SUPPORTED, 0.9, preds)
        assert result.sources == ["https://britannica.com/x"]
