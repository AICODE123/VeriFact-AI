"""
config_loader.py
=================
Loads and caches the application's YAML configuration file, exposing it as a
plain nested dictionary. Kept intentionally simple: a single source of truth
that every other module pulls from instead of hardcoding values.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any, Dict

import yaml

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "settings.yaml"


class ConfigError(Exception):
    """Raised when the configuration file is missing or malformed."""


@functools.lru_cache(maxsize=1)
def load_config(config_path: str | Path = _DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """
    Load the YAML configuration file and return it as a dictionary.

    The result is cached (lru_cache) so the file is only read from disk once
    per process. Use `load_config.cache_clear()` in tests if a fresh read is
    needed.

    Args:
        config_path: Path to the YAML config file.

    Returns:
        Parsed configuration as a nested dictionary.

    Raises:
        ConfigError: If the file cannot be found or parsed.
    """
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"Configuration file not found at: {path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Failed to parse YAML config: {exc}") from exc

    if not isinstance(config, dict):
        raise ConfigError("Configuration file did not parse to a dictionary.")

    return config


def get_project_root() -> Path:
    """Return the absolute path to the project root directory."""
    return Path(__file__).resolve().parent.parent
