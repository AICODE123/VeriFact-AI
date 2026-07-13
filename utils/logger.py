"""
logger.py
=========
Centralized logging configuration for VeriFact AI.

Every module should obtain its logger via `get_logger(__name__)` rather than
configuring logging itself. This guarantees consistent formatting and a
single rotating log file across the whole application.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config.config_loader import get_project_root, load_config

_CONFIGURED = False


def _configure_root_logger() -> None:
    """Configure the root 'verifact' logger once per process."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    config = load_config()
    log_cfg = config.get("logging", {})

    log_dir = get_project_root() / log_cfg.get("log_dir", "logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / log_cfg.get("log_file", "verifact.log")

    level_name = log_cfg.get("level", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger("verifact")
    root_logger.setLevel(level)
    root_logger.propagate = False

    # Avoid duplicate handlers if this somehow runs more than once
    if root_logger.handlers:
        _CONFIGURED = True
        return

    file_handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=int(log_cfg.get("max_bytes", 1_048_576)),
        backupCount=int(log_cfg.get("backup_count", 3)),
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """
    Return a namespaced logger under the 'verifact' hierarchy.

    Args:
        name: Typically `__name__` of the calling module.

    Returns:
        A configured `logging.Logger` instance.
    """
    _configure_root_logger()
    return logging.getLogger(f"verifact.{name}")
