"""
database.py
============
SQLite persistence layer with two responsibilities:

1. History store — every verification query/result is saved so the UI can
   show a "History" page.
2. Offline knowledge base — a local table of several hundred pre-verified
   facts, used as a fallback when the internet is unavailable ("Offline
   Mode") or when the user explicitly enables it.

Two separate SQLite files are used (see config/settings.yaml) so the
offline knowledge base ships as a read-mostly seed file distinct from the
user's growing personal history.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, List, Optional

from config.config_loader import get_project_root, load_config
from models.schemas import HistoryEntry, OfflineFact, VerdictLabel, VerificationResult
from utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseError(Exception):
    """Raised on unrecoverable database errors."""


class Database:
    """Manages both the history DB and the offline knowledge base DB."""

    def __init__(self) -> None:
        config = load_config()
        root = get_project_root()
        self._history_path = root / config["storage"]["history_db_path"]
        self._kb_path = root / config["storage"]["offline_kb_db_path"]
        self._max_history_items = int(config["ui"]["max_history_items"])

        self._history_path.parent.mkdir(parents=True, exist_ok=True)
        self._kb_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_history_db()
        self._init_kb_db()

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    @contextmanager
    def _connect(self, db_path: Path) -> Iterator[sqlite3.Connection]:
        """Yield a SQLite connection with row factory set, closing on exit."""
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            logger.error("Database error on %s: %s", db_path, exc)
            raise DatabaseError(str(exc)) from exc
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Schema initialization
    # ------------------------------------------------------------------

    def _init_history_db(self) -> None:
        with self._connect(self._history_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    claim TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    reason TEXT NOT NULL,
                    sources TEXT NOT NULL,
                    used_offline_kb INTEGER NOT NULL DEFAULT 0,
                    timestamp TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp DESC)")

    def _init_kb_db(self) -> None:
        with self._connect(self._kb_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS offline_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    claim_text TEXT NOT NULL UNIQUE,
                    verdict TEXT NOT NULL,
                    explanation TEXT NOT NULL,
                    source TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general'
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kb_category ON offline_facts(category)")

    # ------------------------------------------------------------------
    # History operations
    # ------------------------------------------------------------------

    def save_result(self, result: VerificationResult) -> None:
        """Persist a VerificationResult to the history table."""
        with self._connect(self._history_path) as conn:
            conn.execute(
                """
                INSERT INTO history (claim, verdict, confidence, reason, sources, used_offline_kb, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.claim,
                    result.verdict.value,
                    result.confidence,
                    result.reason,
                    ", ".join(result.sources),
                    int(result.used_offline_kb),
                    result.timestamp.isoformat(),
                ),
            )
        logger.info("Saved verification result for claim: '%s'", result.claim)

    def get_history(self, limit: Optional[int] = None) -> List[HistoryEntry]:
        """Return past verification results, most recent first."""
        limit = limit or self._max_history_items
        with self._connect(self._history_path) as conn:
            rows = conn.execute(
                "SELECT * FROM history ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()

        return [
            HistoryEntry(
                id=row["id"],
                claim=row["claim"],
                verdict=row["verdict"],
                confidence=row["confidence"],
                reason=row["reason"],
                sources=row["sources"],
                timestamp=row["timestamp"],
            )
            for row in rows
        ]

    def clear_history(self) -> None:
        """Delete all saved history entries."""
        with self._connect(self._history_path) as conn:
            conn.execute("DELETE FROM history")
        logger.info("History cleared.")

    # ------------------------------------------------------------------
    # Offline knowledge base operations
    # ------------------------------------------------------------------

    def search_offline_kb(self, claim: str, search_terms: List[str]) -> Optional[OfflineFact]:
        """
        Search the offline knowledge base for a fact matching the claim.

        Uses a simple case-insensitive substring match across the claim text
        and extracted search terms — sufficient for a curated, few-hundred-row
        offline table without pulling in a full-text search engine.

        Args:
            claim: The user's raw claim.
            search_terms: Key entities/nouns extracted by ClaimProcessor,
                used as fallback match candidates.

        Returns:
            The best-matching OfflineFact, or None if nothing matches.
        """
        candidates = [claim] + search_terms
        with self._connect(self._kb_path) as conn:
            for term in candidates:
                term = term.strip()
                if not term:
                    continue
                rows = conn.execute(
                    "SELECT * FROM offline_facts WHERE claim_text LIKE ? LIMIT 1",
                    (f"%{term}%",),
                ).fetchall()
                if rows:
                    row = rows[0]
                    return OfflineFact(
                        claim_text=row["claim_text"],
                        verdict=VerdictLabel(row["verdict"]),
                        explanation=row["explanation"],
                        source=row["source"],
                        category=row["category"],
                    )
        return None

    def seed_offline_kb(self, facts: List[OfflineFact], overwrite: bool = False) -> int:
        """
        Insert a batch of facts into the offline knowledge base.

        Args:
            facts: Facts to insert.
            overwrite: If True, replace existing rows with matching claim_text.

        Returns:
            Number of facts inserted (or replaced).
        """
        sql = (
            "INSERT OR REPLACE INTO offline_facts (claim_text, verdict, explanation, source, category) "
            "VALUES (?, ?, ?, ?, ?)"
            if overwrite
            else "INSERT OR IGNORE INTO offline_facts (claim_text, verdict, explanation, source, category) "
            "VALUES (?, ?, ?, ?, ?)"
        )
        count = 0
        with self._connect(self._kb_path) as conn:
            for fact in facts:
                cursor = conn.execute(
                    sql,
                    (fact.claim_text, fact.verdict.value, fact.explanation, fact.source, fact.category),
                )
                count += cursor.rowcount if cursor.rowcount > 0 else 0
        logger.info("Seeded %d facts into offline knowledge base.", count)
        return count

    def kb_fact_count(self) -> int:
        """Return the total number of facts stored in the offline knowledge base."""
        with self._connect(self._kb_path) as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM offline_facts").fetchone()
        return int(row["cnt"]) if row else 0


def utcnow_iso() -> str:
    """Return the current UTC time as an ISO-8601 string (helper for tests/UI)."""
    return datetime.now(timezone.utc).isoformat()
