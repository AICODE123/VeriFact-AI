"""
pipeline.py
===========
Top-level orchestrator that wires together every core module into the full
pipeline described in the spec:

Claim -> Claim Processing -> NER -> Search -> Retrieve Evidence ->
Semantic Similarity -> NLI -> Decision -> Explanation

This is the single entry point the UI (or tests, or a CLI) should call.
Keeping orchestration separate from the individual modules keeps each module
independently testable and swappable.
"""

from __future__ import annotations

from dataclasses import dataclass

from config.config_loader import load_config
from core.claim_processor import ClaimProcessor, ClaimProcessorError
from core.database import Database
from core.evidence_retriever import EvidenceRetriever, EvidenceRetrieverError
from core.explainer import Explainer
from core.search_engine import SearchEngine, SearchEngineError
from core.verifier import Verifier, VerifierError
from models.schemas import VerdictLabel, VerificationResult
from utils.logger import get_logger

logger = get_logger(__name__)


class PipelineError(Exception):
    """Raised when the pipeline cannot produce a result at all (rare)."""


@dataclass
class PipelineComponents:
    """Bundle of lazily-initialized, potentially-heavy pipeline components."""

    claim_processor: ClaimProcessor
    search_engine: SearchEngine
    evidence_retriever: EvidenceRetriever
    verifier: Verifier
    explainer: Explainer
    database: Database


class VerificationPipeline:
    """
    Orchestrates the end-to-end fact verification process.

    Heavy AI models (spaCy, sentence-transformers, the NLI model) are loaded
    once when the pipeline is constructed, then reused across every call to
    `run()`. In the Streamlit app this object should be created once and
    cached (e.g. via `st.cache_resource`).
    """

    def __init__(self) -> None:
        logger.info("Initializing VerificationPipeline components (this may take a moment)...")
        self._components = PipelineComponents(
            claim_processor=ClaimProcessor(),
            search_engine=SearchEngine(),
            evidence_retriever=EvidenceRetriever(),
            verifier=Verifier(),
            explainer=Explainer(),
            database=Database(),
        )
        logger.info("VerificationPipeline ready.")

    def run(self, raw_claim: str, offline_mode: bool = False) -> VerificationResult:
        """
        Run the full verification pipeline for a single claim.

        Args:
            raw_claim: The user's natural-language claim.
            offline_mode: If True, skip live web search entirely and only
                consult the local offline knowledge base.

        Returns:
            A VerificationResult, always populated (falls back to
            "Insufficient Evidence" rather than raising, wherever possible).
        """
        c = self._components

        try:
            claim_info = c.claim_processor.process(raw_claim)
        except ClaimProcessorError as exc:
            raise PipelineError(str(exc)) from exc

        # Offline mode (explicit or forced by a search failure): try the
        # local knowledge base first.
        if offline_mode:
            offline_result = self._try_offline_kb(raw_claim, claim_info.entities + claim_info.key_nouns)
            if offline_result is not None:
                c.database.save_result(offline_result)
                return offline_result
            return self._insufficient_evidence_result(
                raw_claim,
                reason="Offline mode is enabled and no matching fact was found in the local knowledge base.",
                used_offline_kb=True,
            )

        # Live pipeline: search -> scrape -> rank -> NLI -> aggregate -> explain
        try:
            search_results = c.search_engine.search(claim_info.search_query)
        except SearchEngineError as exc:
            logger.warning("Live search failed (%s); falling back to offline knowledge base.", exc)
            offline_result = self._try_offline_kb(raw_claim, claim_info.entities + claim_info.key_nouns)
            if offline_result is not None:
                c.database.save_result(offline_result)
                return offline_result
            result = self._insufficient_evidence_result(
                raw_claim, reason=f"Web search is unavailable right now ({exc}) and no offline match was found."
            )
            c.database.save_result(result)
            return result

        if not search_results:
            offline_result = self._try_offline_kb(raw_claim, claim_info.entities + claim_info.key_nouns)
            if offline_result is not None:
                c.database.save_result(offline_result)
                return offline_result
            result = self._insufficient_evidence_result(
                raw_claim, reason="No trusted sources were found for this claim."
            )
            c.database.save_result(result)
            return result

        try:
            raw_chunks = c.evidence_retriever.fetch_and_chunk(search_results)
            ranked_chunks = c.evidence_retriever.rank_by_relevance(raw_claim, raw_chunks)
        except EvidenceRetrieverError as exc:
            result = self._insufficient_evidence_result(raw_claim, reason=f"Evidence retrieval failed: {exc}")
            c.database.save_result(result)
            return result

        if not ranked_chunks:
            offline_result = self._try_offline_kb(raw_claim, claim_info.entities + claim_info.key_nouns)
            if offline_result is not None:
                c.database.save_result(offline_result)
                return offline_result
            result = self._insufficient_evidence_result(
                raw_claim, reason="Trusted sources were found, but none contained content relevant enough to the claim."
            )
            c.database.save_result(result)
            return result

        try:
            predictions = c.verifier.predict_batch(raw_claim, ranked_chunks)
            verdict, confidence = c.verifier.aggregate(predictions)
        except VerifierError as exc:
            result = self._insufficient_evidence_result(raw_claim, reason=f"Verification model failed: {exc}")
            c.database.save_result(result)
            return result

        result = c.explainer.build_result(
            claim=raw_claim,
            verdict=verdict,
            confidence=confidence,
            predictions=predictions,
            used_offline_kb=False,
        )
        c.database.save_result(result)
        return result

    def _try_offline_kb(self, claim: str, search_terms: list[str]) -> VerificationResult | None:
        """Attempt to answer the claim from the offline knowledge base."""
        fact = self._components.database.search_offline_kb(claim, search_terms)
        if fact is None:
            return None

        return VerificationResult(
            claim=claim,
            verdict=fact.verdict,
            confidence=0.9,  # curated facts are treated as high-confidence
            reason=fact.explanation,
            evidence_chunks=[],
            sources=[fact.source],
            used_offline_kb=True,
        )

    @staticmethod
    def _insufficient_evidence_result(raw_claim: str, reason: str, used_offline_kb: bool = False) -> VerificationResult:
        """Build a graceful fallback result when the pipeline cannot reach a verdict."""
        return VerificationResult(
            claim=raw_claim,
            verdict=VerdictLabel.INSUFFICIENT_EVIDENCE,
            confidence=0.0,
            reason=reason,
            evidence_chunks=[],
            sources=[],
            used_offline_kb=used_offline_kb,
        )
