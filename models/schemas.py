"""
schemas.py
==========
Typed dataclasses shared across the VeriFact AI pipeline. Keeping these in
one place gives every module (search, retrieval, verification, UI, database)
a single, consistent contract to pass data through.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class VerdictLabel(str, Enum):
    """Final verification labels the system can output."""

    SUPPORTED = "Supported"
    CONTRADICTED = "Contradicted"
    INSUFFICIENT_EVIDENCE = "Insufficient Evidence"


class NLILabel(str, Enum):
    """Raw labels produced by the Natural Language Inference model."""

    ENTAILMENT = "entailment"
    CONTRADICTION = "contradiction"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class ExtractedClaimInfo:
    """Structured information extracted from the raw user claim via spaCy."""

    original_claim: str
    entities: List[str] = field(default_factory=list)
    organizations: List[str] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    key_nouns: List[str] = field(default_factory=list)
    search_query: str = ""


@dataclass(frozen=True)
class SearchResult:
    """A single trusted search result before scraping."""

    title: str
    url: str
    domain: str
    snippet: str = ""


@dataclass(frozen=True)
class EvidenceChunk:
    """A chunk of scraped text along with its provenance and relevance score."""

    text: str
    source_url: str
    source_title: str
    similarity_score: float = 0.0


@dataclass(frozen=True)
class NLIPrediction:
    """Output of running the NLI model over one (claim, evidence chunk) pair."""

    evidence: EvidenceChunk
    label: NLILabel
    entailment_prob: float
    contradiction_prob: float
    neutral_prob: float


@dataclass
class VerificationResult:
    """
    Final, explainable output of the verification pipeline. This is the
    object the Streamlit UI renders and the database persists.
    """

    claim: str
    verdict: VerdictLabel
    confidence: float  # 0.0 - 1.0
    reason: str
    evidence_chunks: List[EvidenceChunk] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    used_offline_kb: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def confidence_percent(self) -> str:
        """Return confidence formatted as a percentage string, e.g. '97%'."""
        return f"{round(self.confidence * 100)}%"


@dataclass(frozen=True)
class OfflineFact:
    """A single verified fact stored in the local offline knowledge base."""

    claim_text: str
    verdict: VerdictLabel
    explanation: str
    source: str
    category: str = "general"


@dataclass(frozen=True)
class HistoryEntry:
    """A persisted record of a past verification, shown in the History page."""

    id: Optional[int]
    claim: str
    verdict: str
    confidence: float
    reason: str
    sources: str  # stored as comma-separated string in SQLite
    timestamp: str
