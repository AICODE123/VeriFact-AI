"""
evidence_retriever.py
======================
STEPS 5-8 of the pipeline:
  5. Download webpage & extract clean text
  6. Split into overlapping chunks
  7. Generate embeddings via Sentence Transformers
  8. Retrieve the top-k most semantically relevant chunks for the claim

This module intentionally separates "fetching" from "ranking" so each half
can be tested and mocked independently (network calls are the flakiest part
of any pipeline test suite).
"""

from __future__ import annotations

import functools
from typing import List

import requests
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer, util

from config.config_loader import load_config
from models.schemas import EvidenceChunk, SearchResult
from utils.logger import get_logger
from utils.text_utils import chunk_text, clean_text

logger = get_logger(__name__)


class EvidenceRetrieverError(Exception):
    """Raised when evidence cannot be retrieved for any of the search results."""


@functools.lru_cache(maxsize=1)
def _load_embedding_model() -> SentenceTransformer:
    """Load and cache the sentence-transformers embedding model."""
    config = load_config()
    model_name = config["models"]["embedding_model"]
    logger.info("Loading embedding model '%s'...", model_name)
    model = SentenceTransformer(model_name)
    logger.info("Embedding model loaded.")
    return model


class EvidenceRetriever:
    """Fetches web pages, chunks their text, and ranks chunks by relevance."""

    def __init__(self) -> None:
        config = load_config()
        self._model = _load_embedding_model()
        self._timeout = int(config["search"]["request_timeout_seconds"])
        self._user_agent = config["search"]["user_agent"]
        self._max_pages = int(config["search"]["max_pages_to_scrape"])
        self._chunk_size = int(config["retrieval"]["chunk_size_words"])
        self._overlap = int(config["retrieval"]["chunk_overlap_words"])
        self._min_chunk_words = int(config["retrieval"]["min_chunk_words"])
        self._top_k = int(config["retrieval"]["top_k_chunks"])
        self._min_similarity = float(config["verification"]["min_similarity_threshold"])

    def fetch_and_chunk(self, results: List[SearchResult]) -> List[EvidenceChunk]:
        """
        Download each search result page, clean and chunk its text.

        Individual page failures (timeout, 404, parsing error) are logged and
        skipped rather than aborting the whole pipeline.

        Args:
            results: Trusted search results to scrape.

        Returns:
            Flat list of EvidenceChunk (similarity_score not yet set).
        """
        all_chunks: List[EvidenceChunk] = []
        headers = {"User-Agent": self._user_agent}

        for result in results[: self._max_pages]:
            try:
                response = requests.get(result.url, headers=headers, timeout=self._timeout)
                response.raise_for_status()
            except requests.RequestException as exc:
                logger.warning("Failed to fetch %s: %s", result.url, exc)
                continue

            try:
                page_text = self._extract_main_text(response.text)
            except Exception as exc:  # noqa: BLE001 - HTML parsing can fail unpredictably
                logger.warning("Failed to parse %s: %s", result.url, exc)
                continue

            cleaned = clean_text(page_text)
            if not cleaned:
                continue

            chunks = chunk_text(
                cleaned,
                chunk_size_words=self._chunk_size,
                overlap_words=self._overlap,
                min_chunk_words=self._min_chunk_words,
            )
            for chunk in chunks:
                all_chunks.append(
                    EvidenceChunk(
                        text=chunk,
                        source_url=result.url,
                        source_title=result.title or result.domain,
                    )
                )

        logger.info("Retrieved %d evidence chunks from %d pages", len(all_chunks), min(len(results), self._max_pages))
        return all_chunks

    def rank_by_relevance(self, claim: str, chunks: List[EvidenceChunk]) -> List[EvidenceChunk]:
        """
        Embed the claim and all chunks, then return the top-k most similar
        chunks (cosine similarity), filtered by the minimum similarity
        threshold.

        Args:
            claim: The original user claim.
            chunks: Candidate evidence chunks (unranked).

        Returns:
            Top-k EvidenceChunk objects sorted by descending similarity_score.
        """
        if not chunks:
            return []

        claim_embedding = self._model.encode(claim, convert_to_tensor=True)
        chunk_texts = [c.text for c in chunks]
        chunk_embeddings = self._model.encode(chunk_texts, convert_to_tensor=True)

        similarities = util.cos_sim(claim_embedding, chunk_embeddings)[0]

        scored_chunks = [
            EvidenceChunk(
                text=chunk.text,
                source_url=chunk.source_url,
                source_title=chunk.source_title,
                similarity_score=float(similarities[i]),
            )
            for i, chunk in enumerate(chunks)
        ]

        relevant = [c for c in scored_chunks if c.similarity_score >= self._min_similarity]
        relevant.sort(key=lambda c: c.similarity_score, reverse=True)

        logger.info(
            "Ranked %d chunks; %d passed similarity threshold %.2f",
            len(scored_chunks),
            len(relevant),
            self._min_similarity,
        )
        return relevant[: self._top_k]

    @staticmethod
    def _extract_main_text(html: str) -> str:
        """Strip scripts/styles/nav and extract readable body text from HTML."""
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
            tag.decompose()

        # Prefer <article> or <main> if present (common on Wikipedia/Britannica/news sites)
        container = soup.find("article") or soup.find("main") or soup

        paragraphs = [p.get_text(" ", strip=True) for p in container.find_all("p")]
        return " ".join(p for p in paragraphs if p)
