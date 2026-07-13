"""Pytest configuration: ensure the project root is importable as a package root."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
