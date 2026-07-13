"""
claim_processor.py
===================
STEP 1-3 of the pipeline: receive the raw user claim, run Named Entity
Recognition over it with spaCy, and generate an optimized search query.

Design notes:
- spaCy's model is loaded once (module-level singleton via functools.lru_cache)
  since loading it repeatedly is expensive.
- Query generation is heuristic: prioritize named entities (people, orgs,
  locations, dates) over generic nouns, since they carry the most discriminating
  signal for search engines.
"""

from __future__ import annotations

import functools
from typing import List

import spacy
from spacy.language import Language

from config.config_loader import load_config
from models.schemas import ExtractedClaimInfo
from utils.logger import get_logger

logger = get_logger(__name__)

# spaCy entity labels we care about, grouped by the ExtractedClaimInfo field
# they map to.
_ORG_LABELS = {"ORG"}
_LOCATION_LABELS = {"GPE", "LOC", "FAC"}
_DATE_LABELS = {"DATE", "TIME"}
_GENERIC_ENTITY_LABELS = {"PERSON", "NORP", "EVENT", "PRODUCT", "WORK_OF_ART"}


class ClaimProcessorError(Exception):
    """Raised when the claim cannot be processed (e.g. empty input)."""


@functools.lru_cache(maxsize=1)
def _load_spacy_model() -> Language:
    """Load and cache the spaCy language model defined in configuration."""
    config = load_config()
    model_name = config["models"]["spacy_model"]
    try:
        nlp = spacy.load(model_name)
    except OSError as exc:
        logger.error("spaCy model '%s' not found. Run: python -m spacy download %s", model_name, model_name)
        raise ClaimProcessorError(
            f"spaCy model '{model_name}' is not installed. "
            f"Run `python -m spacy download {model_name}` and try again."
        ) from exc
    logger.info("Loaded spaCy model '%s'", model_name)
    return nlp


class ClaimProcessor:
    """Extracts structured information from a raw natural-language claim."""

    def __init__(self) -> None:
        self._nlp = _load_spacy_model()

    def process(self, raw_claim: str) -> ExtractedClaimInfo:
        """
        Run NER over the claim and build an optimized search query.

        Args:
            raw_claim: The user-provided factual claim, e.g.
                "The Eiffel Tower is located in Berlin."

        Returns:
            ExtractedClaimInfo with entities and a generated search query.

        Raises:
            ClaimProcessorError: If `raw_claim` is empty or whitespace-only.
        """
        claim = raw_claim.strip()
        if not claim:
            raise ClaimProcessorError("Claim text cannot be empty.")

        doc = self._nlp(claim)

        organizations = self._unique([ent.text for ent in doc.ents if ent.label_ in _ORG_LABELS])
        locations = self._unique([ent.text for ent in doc.ents if ent.label_ in _LOCATION_LABELS])
        dates = self._unique([ent.text for ent in doc.ents if ent.label_ in _DATE_LABELS])
        generic_entities = self._unique(
            [ent.text for ent in doc.ents if ent.label_ in _GENERIC_ENTITY_LABELS]
        )
        all_entities = self._unique(organizations + locations + dates + generic_entities)

        key_nouns = self._unique(
            [
                chunk.root.text
                for chunk in doc.noun_chunks
                if chunk.root.pos_ in ("NOUN", "PROPN")
            ]
        )

        search_query = self._build_search_query(
            claim=claim,
            organizations=organizations,
            locations=locations,
            dates=dates,
            generic_entities=generic_entities,
            key_nouns=key_nouns,
        )

        logger.info("Processed claim -> query: '%s'", search_query)

        return ExtractedClaimInfo(
            original_claim=claim,
            entities=all_entities,
            organizations=organizations,
            dates=dates,
            locations=locations,
            key_nouns=key_nouns,
            search_query=search_query,
        )

    @staticmethod
    def _build_search_query(
        claim: str,
        organizations: List[str],
        locations: List[str],
        dates: List[str],
        generic_entities: List[str],
        key_nouns: List[str],
    ) -> str:
        """
        Build a concise, high-signal search query from extracted entities.

        Prioritization: named entities (subject) + a fact-seeking anchor word
        (e.g. "location", "founded", "population") beat dumping the whole
        claim verbatim into the search box.
        """
        # The "subject" of the claim: prefer proper entities over generic nouns
        subject_terms = (generic_entities + organizations + locations)[:2]
        if not subject_terms:
            subject_terms = key_nouns[:2]
        if not subject_terms:
            # Fall back to the raw claim if NER found nothing useful
            return claim

        anchor = ""
        if locations:
            anchor = "location"
        elif dates:
            anchor = "date facts"
        elif organizations:
            anchor = "official information"

        query_parts = subject_terms + ([anchor] if anchor else [])
        return " ".join(query_parts).strip()

    @staticmethod
    def _unique(items: List[str]) -> List[str]:
        """Deduplicate a list while preserving order."""
        seen = set()
        result = []
        for item in items:
            normalized = item.strip()
            if normalized and normalized.lower() not in seen:
                seen.add(normalized.lower())
                result.append(normalized)
        return result
