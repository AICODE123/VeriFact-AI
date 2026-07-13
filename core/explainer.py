"""
explainer.py
============
Explainable AI layer. Never surface a bare "True"/"False" — always produce a
Decision + Confidence + Reason + Evidence + Sources bundle (per project spec).

This module takes the raw output of Verifier.aggregate() plus the ranked
NLI predictions and turns them into a polished VerificationResult, including
a natural-language `reason` string.
"""

from __future__ import annotations

from typing import List

from models.schemas import (
    EvidenceChunk,
    NLIPrediction,
    VerdictLabel,
    VerificationResult,
)
from utils.logger import get_logger
from utils.text_utils import truncate

logger = get_logger(__name__)


class Explainer:
    """Builds a final, explainable VerificationResult."""

    def build_result(
        self,
        claim: str,
        verdict: VerdictLabel,
        confidence: float,
        predictions: List[NLIPrediction],
        used_offline_kb: bool = False,
    ) -> VerificationResult:
        """
        Assemble the final explainable result shown in the UI.

        Args:
            claim: Original user claim.
            verdict: Aggregated verdict label.
            confidence: Aggregated confidence score (0-1).
            predictions: Per-chunk NLI predictions that fed the aggregation.
            used_offline_kb: Whether this result came from the offline
                knowledge base rather than a live web search.

        Returns:
            A fully-populated VerificationResult.
        """
        reason = self._build_reason(claim, verdict, predictions)
        evidence_chunks = self._select_supporting_evidence(verdict, predictions)
        sources = self._unique_sources(evidence_chunks)

        result = VerificationResult(
            claim=claim,
            verdict=verdict,
            confidence=confidence,
            reason=reason,
            evidence_chunks=evidence_chunks,
            sources=sources,
            used_offline_kb=used_offline_kb,
        )

        logger.info("Built result: %s (%.0f%%) for claim: '%s'", verdict.value, confidence * 100, claim)
        return result

    def _build_reason(self, claim: str, verdict: VerdictLabel, predictions: List[NLIPrediction]) -> str:
        """Generate a natural-language explanation of why this verdict was reached."""
        if verdict == VerdictLabel.INSUFFICIENT_EVIDENCE:
            if not predictions:
                return (
                    f'No sufficiently relevant evidence was found from trusted sources '
                    f'to verify the claim: "{claim}". This may mean the claim is too '
                    f'vague, too recent, or not covered by the trusted domains searched.'
                )
            return (
                f'Evidence was found, but it was not conclusive enough to confidently '
                f'confirm or refute the claim: "{claim}". The retrieved sources were '
                f'either only tangentially related or gave conflicting signals.'
            )

        top_prediction = max(
            predictions,
            key=lambda p: p.entailment_prob if verdict == VerdictLabel.SUPPORTED else p.contradiction_prob,
        )
        evidence_snippet = truncate(top_prediction.evidence.text, max_chars=220)

        if verdict == VerdictLabel.SUPPORTED:
            return (
                f'The claim states: "{claim}". Trusted sources consistently support this. '
                f'For example, {top_prediction.evidence.source_title} states: "{evidence_snippet}"'
            )

        return (
            f'The claim states: "{claim}". Trusted sources contradict this. '
            f'For example, {top_prediction.evidence.source_title} states: "{evidence_snippet}"'
        )

    @staticmethod
    def _select_supporting_evidence(
        verdict: VerdictLabel, predictions: List[NLIPrediction], max_items: int = 5
    ) -> List[EvidenceChunk]:
        """Pick the evidence chunks most relevant to the final verdict, best-first."""
        if not predictions:
            return []

        if verdict == VerdictLabel.SUPPORTED:
            sorted_preds = sorted(predictions, key=lambda p: p.entailment_prob, reverse=True)
        elif verdict == VerdictLabel.CONTRADICTED:
            sorted_preds = sorted(predictions, key=lambda p: p.contradiction_prob, reverse=True)
        else:
            sorted_preds = sorted(predictions, key=lambda p: p.evidence.similarity_score, reverse=True)

        return [p.evidence for p in sorted_preds[:max_items]]

    @staticmethod
    def _unique_sources(evidence_chunks: List[EvidenceChunk]) -> List[str]:
        """Deduplicate source URLs while preserving order."""
        seen = set()
        sources = []
        for chunk in evidence_chunks:
            if chunk.source_url not in seen:
                seen.add(chunk.source_url)
                sources.append(chunk.source_url)
        return sources
