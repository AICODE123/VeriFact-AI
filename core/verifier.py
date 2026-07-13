"""
verifier.py
============
STEPS 9-10 of the pipeline:
  9. Run a pretrained HuggingFace Natural Language Inference (NLI) model over
     each (evidence chunk, claim) pair to classify it as entailment /
     contradiction / neutral.
  10. Aggregate the per-chunk predictions into one final decision with an
      overall confidence score.

The NLI model treats each evidence chunk as the "premise" and the user's
claim as the "hypothesis": does the premise entail, contradict, or say
nothing relevant about the hypothesis?
"""

from __future__ import annotations

import functools
from typing import List, Tuple

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from config.config_loader import load_config
from models.schemas import EvidenceChunk, NLILabel, NLIPrediction, VerdictLabel
from utils.logger import get_logger

logger = get_logger(__name__)


class VerifierError(Exception):
    """Raised when the NLI model fails to load or run."""


@functools.lru_cache(maxsize=1)
def _load_nli_model() -> Tuple[AutoTokenizer, AutoModelForSequenceClassification]:
    """Load and cache the tokenizer + NLI model defined in configuration."""
    config = load_config()
    model_name = config["models"]["nli_model"]
    logger.info("Loading NLI model '%s'...", model_name)
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        model.eval()
    except Exception as exc:  # noqa: BLE001 - HF download/load can fail many ways
        raise VerifierError(f"Failed to load NLI model '{model_name}': {exc}") from exc
    logger.info("NLI model loaded.")
    return tokenizer, model


class Verifier:
    """Runs NLI over evidence chunks and aggregates a final verdict."""

    def __init__(self) -> None:
        config = load_config()
        self._tokenizer, self._model = _load_nli_model()
        self._max_length = int(config["models"]["nli_max_length"])
        self._min_confidence = float(config["verification"]["min_confidence_threshold"])
        self._min_evidence_chunks = int(config["verification"]["min_evidence_chunks"])

        # cross-encoder/nli-deberta-v3-small label order: 0=contradiction, 1=entailment, 2=neutral
        # We read the model config to stay robust to label-order differences across checkpoints.
        id2label = {int(k): v.lower() for k, v in self._model.config.id2label.items()}
        self._label_index = {
            NLILabel.CONTRADICTION: self._find_index(id2label, "contra"),
            NLILabel.ENTAILMENT: self._find_index(id2label, "entail"),
            NLILabel.NEUTRAL: self._find_index(id2label, "neutral"),
        }

    def predict_batch(self, claim: str, evidence_chunks: List[EvidenceChunk]) -> List[NLIPrediction]:
        """
        Run NLI for each evidence chunk against the claim.

        Args:
            claim: The user's original claim (used as the NLI hypothesis).
            evidence_chunks: Ranked, relevant evidence chunks (the premises).

        Returns:
            List of NLIPrediction, one per input chunk.
        """
        predictions: List[NLIPrediction] = []

        for chunk in evidence_chunks:
            inputs = self._tokenizer(
                chunk.text,
                claim,
                truncation=True,
                max_length=self._max_length,
                return_tensors="pt",
            )
            with torch.no_grad():
                logits = self._model(**inputs).logits
                probs = torch.softmax(logits, dim=-1)[0]

            entailment_prob = float(probs[self._label_index[NLILabel.ENTAILMENT]])
            contradiction_prob = float(probs[self._label_index[NLILabel.CONTRADICTION]])
            neutral_prob = float(probs[self._label_index[NLILabel.NEUTRAL]])

            best_label = max(
                [
                    (NLILabel.ENTAILMENT, entailment_prob),
                    (NLILabel.CONTRADICTION, contradiction_prob),
                    (NLILabel.NEUTRAL, neutral_prob),
                ],
                key=lambda pair: pair[1],
            )[0]

            predictions.append(
                NLIPrediction(
                    evidence=chunk,
                    label=best_label,
                    entailment_prob=entailment_prob,
                    contradiction_prob=contradiction_prob,
                    neutral_prob=neutral_prob,
                )
            )

        return predictions

    def aggregate(self, predictions: List[NLIPrediction]) -> Tuple[VerdictLabel, float]:
        """
        Aggregate per-chunk NLI predictions into one final verdict + confidence.

        Aggregation strategy: weight each chunk's vote by its own prediction
        confidence and by the evidence chunk's semantic similarity score, then
        compare total "support" vs total "contradict" weight. This means a
        single highly-confident, highly-relevant contradicting chunk can
        outweigh several weak/neutral ones (mirrors how a human fact-checker
        would treat a single authoritative contradiction).

        Args:
            predictions: Output of `predict_batch`.

        Returns:
            (verdict, confidence) tuple. confidence is in [0, 1].
        """
        if len(predictions) < self._min_evidence_chunks:
            return VerdictLabel.INSUFFICIENT_EVIDENCE, 0.0

        support_weight = 0.0
        contradict_weight = 0.0

        for pred in predictions:
            relevance = max(pred.evidence.similarity_score, 0.0)
            support_weight += pred.entailment_prob * (0.5 + 0.5 * relevance)
            contradict_weight += pred.contradiction_prob * (0.5 + 0.5 * relevance)

        total_weight = support_weight + contradict_weight
        if total_weight == 0:
            return VerdictLabel.INSUFFICIENT_EVIDENCE, 0.0

        if support_weight >= contradict_weight:
            confidence = support_weight / (support_weight + contradict_weight)
            verdict = VerdictLabel.SUPPORTED
        else:
            confidence = contradict_weight / (support_weight + contradict_weight)
            verdict = VerdictLabel.CONTRADICTED

        if confidence < self._min_confidence:
            return VerdictLabel.INSUFFICIENT_EVIDENCE, confidence

        return verdict, confidence

    @staticmethod
    def _find_index(id2label: dict, substring: str) -> int:
        """Find the label index whose text contains `substring` (case-insensitive)."""
        for idx, label in id2label.items():
            if substring in label:
                return idx
        raise VerifierError(f"Could not find NLI label containing '{substring}' in model config: {id2label}")
