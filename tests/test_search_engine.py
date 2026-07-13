"""Unit tests for core/search_engine.py (domain filtering logic)."""

from __future__ import annotations

from unittest.mock import patch

from core.search_engine import SearchEngine


class TestExtractDomain:
    def test_strips_www_prefix(self):
        assert SearchEngine._extract_domain("https://www.britannica.com/place/Paris") == "britannica.com"

    def test_keeps_subdomain(self):
        assert SearchEngine._extract_domain("https://en.wikipedia.org/wiki/Paris") == "en.wikipedia.org"

    def test_invalid_url_returns_empty(self):
        assert SearchEngine._extract_domain("not a url") == ""


class TestIsTrusted:
    def _make_engine(self):
        with patch("core.search_engine.load_config") as mock_config:
            mock_config.return_value = {
                "search": {
                    "max_results": 5,
                    "trusted_domains": ["wikipedia.org", "britannica.com", ".gov", ".edu"],
                    "user_agent": "test-agent",
                }
            }
            return SearchEngine()

    def test_exact_domain_match(self):
        engine = self._make_engine()
        assert engine._is_trusted("britannica.com") is True

    def test_subdomain_match(self):
        engine = self._make_engine()
        assert engine._is_trusted("en.wikipedia.org") is True

    def test_gov_suffix_match(self):
        engine = self._make_engine()
        assert engine._is_trusted("nasa.gov") is True

    def test_untrusted_domain_rejected(self):
        engine = self._make_engine()
        assert engine._is_trusted("randomblog.com") is False

    def test_lookalike_domain_rejected(self):
        engine = self._make_engine()
        # "notwikipedia.org" should NOT match "wikipedia.org"
        assert engine._is_trusted("notwikipedia.org") is False
