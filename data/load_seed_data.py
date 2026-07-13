"""
load_seed_data.py
==================
One-off script to (re)populate the offline knowledge base SQLite database
from the curated facts in `data/seed_facts.py`.

Usage:
    python data/load_seed_data.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as a standalone script from the project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.database import Database  # noqa: E402
from data.seed_facts import get_all_offline_facts  # noqa: E402
from utils.logger import get_logger  # noqa: E402

logger = get_logger(__name__)


def main() -> None:
    """Load all curated offline facts into the offline knowledge base."""
    db = Database()
    facts = get_all_offline_facts()
    inserted = db.seed_offline_kb(facts, overwrite=True)
    total = db.kb_fact_count()
    print(f"Inserted/updated {inserted} facts. Offline knowledge base now has {total} total facts.")


if __name__ == "__main__":
    main()
