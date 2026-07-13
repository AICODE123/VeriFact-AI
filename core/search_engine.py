"""
search_engine.py
=================
STEP 4 of the pipeline: search the web via DuckDuckGo and filter results down
to a trusted-domain allowlist (.gov, .edu, who.int, britannica.com, etc).

Using DuckDuckGo (via the `duckduckgo-search` / `ddgs` package) avoids the
need for a paid search API key, which keeps this project runnable by
students without any account setup.
"""

from __future__ import annotations

from typing import List
from urllib.parse import urlparse

from config.config_loader import load_config
from models.schemas import SearchResult
from utils.logger import get_logger

logger = get_logger(__name__)


class SearchEngineError(Exception):
    """Raised when the search backend fails or is unreachable."""


class SearchEngine:
    """Performs web search and filters results to trusted domains only."""

    def __init__(self) -> None:
        config = load_config()
        search_cfg = config["search"]
        self._max_results = int(search_cfg["max_results"])
        self._trusted_domains: List[str] = search_cfg["trusted_domains"]
        self._user_agent = search_cfg["user_agent"]
        self._disable_domain_filter = bool(search_cfg.get("disable_domain_filter", False))

    def search(self, query: str) -> List[SearchResult]:
        """
        Search the web and return only results from trusted domains.

        Args:
            query: The optimized search query produced by ClaimProcessor.

        Returns:
            List of SearchResult objects, trusted domains only, best-first.

        Raises:
            SearchEngineError: If the search backend cannot be reached.
        """
        try:
            from ddgs import DDGS  # local import: optional heavy dependency
        except ImportError:
            try:
                from duckduckgo_search import DDGS  # fallback for older package name
            except ImportError as exc:
                raise SearchEngineError(
                    "Neither 'ddgs' nor 'duckduckgo_search' is installed. "
                    "Run: pip install ddgs"
                ) from exc

        logger.info("Searching web for query: '%s'", query)
        raw_results = []
        try:
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=self._max_results * 3))
        except Exception as exc:  # noqa: BLE001 - external network call, broad by necessity
            logger.warning("Search backend error: %s", exc)
            raise SearchEngineError(f"Web search failed: {exc}") from exc

        trusted_results: List[SearchResult] = []
        for item in raw_results:
            url = item.get("href") or item.get("url", "")
            if not url:
                continue
            domain = self._extract_domain(url)
            if not self._is_trusted(domain):
                continue
            trusted_results.append(
                SearchResult(
                    title=item.get("title", "").strip(),
                    url=url,
                    domain=domain,
                    snippet=item.get("body", "").strip(),
                )
            )
            if len(trusted_results) >= self._max_results:
                break

        logger.info("Found %d trusted results out of %d raw results", len(trusted_results), len(raw_results))
        return trusted_results

    def _is_trusted(self, domain: str) -> bool:
        """Check whether a domain matches or is a subdomain of a trusted entry."""
        if self._disable_domain_filter:
            return True
        for trusted in self._trusted_domains:
            trusted = trusted.lower().lstrip(".")
            if domain == trusted or domain.endswith("." + trusted):
                return True
        return False

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract the lowercase netloc (domain) from a URL."""
        try:
            netloc = urlparse(url).netloc.lower()
            return netloc[4:] if netloc.startswith("www.") else netloc
        except ValueError:
            return ""