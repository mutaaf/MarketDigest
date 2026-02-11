"""Custom data source fetcher — HTTP APIs, RSS feeds, and CSV files."""

import csv
import os
from pathlib import Path
from typing import Any

import requests

from config.settings import PROJECT_ROOT
from src.fetchers.base import BaseFetcher, FetcherError
from src.utils.logging_config import get_logger

logger = get_logger("custom_fetcher")


class CustomSourceFetcher(BaseFetcher):
    """Fetcher for user-defined custom data sources (HTTP, RSS, CSV)."""

    def __init__(self, source_config: dict):
        super().__init__()
        self.config = source_config
        self._source_id = source_config.get("id", "custom")
        self._cache_ttl = source_config.get("cache_ttl", 300)

    @property
    def api_name(self) -> str:
        return f"custom_{self._source_id}"

    @property
    def cache_ttl(self) -> int:
        return self._cache_ttl

    # ── Public API ───────────────────────────────────────────────

    def fetch(self) -> dict | list | None:
        """Fetch data from this custom source. Dispatches by type."""
        src_type = self.config.get("type", "http")
        cache_key = f"custom_source:{self._source_id}"

        if src_type == "http":
            return self.fetch_with_cache(cache_key, self._fetch_http)
        elif src_type == "rss":
            return self.fetch_with_cache(cache_key, self._fetch_rss)
        elif src_type == "csv":
            return self.fetch_with_cache(cache_key, self._fetch_csv)
        else:
            logger.warning(f"Unknown custom source type: {src_type}")
            return None

    def test_connection(self) -> dict:
        """Test the source connection. Returns {success, message}."""
        src_type = self.config.get("type", "http")
        try:
            if src_type == "http":
                data = self._fetch_http()
                count = len(data) if isinstance(data, list) else 1
                return {"success": True, "message": f"OK — fetched {count} item(s)"}
            elif src_type == "rss":
                data = self._fetch_rss()
                return {"success": True, "message": f"OK — {len(data)} items"}
            elif src_type == "csv":
                data = self._fetch_csv()
                return {"success": True, "message": f"OK — {len(data)} rows"}
            else:
                return {"success": False, "message": f"Unknown type: {src_type}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ── HTTP ─────────────────────────────────────────────────────

    def _fetch_http(self) -> dict | list:
        """Fetch from an HTTP API with URL template substitution and auth."""
        url = self.config.get("url", "")
        instruments = self.config.get("instruments", [])
        auth = self.config.get("auth", {})
        response_root = self.config.get("response_root")
        response_mapping = self.config.get("response_mapping", {})

        # Resolve auth env var
        api_key = ""
        if auth.get("env_var"):
            api_key = os.environ.get(auth["env_var"], "")

        results = []

        targets = instruments if instruments else [""]
        for symbol in targets:
            rendered_url = url.replace("{symbol}", symbol).replace("{api_key}", api_key)

            # Auth injection
            headers = {}
            auth_type = auth.get("type", "none")
            if auth_type == "bearer" and api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            elif auth_type == "header" and api_key:
                header_name = auth.get("header_name", "X-API-Key")
                headers[header_name] = api_key

            resp = requests.get(rendered_url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            # Navigate to response_root (dot-notation)
            if response_root:
                for key in response_root.split("."):
                    if isinstance(data, dict):
                        data = data.get(key, {})

            # Apply field mapping
            if response_mapping and isinstance(data, dict):
                mapped = {"symbol": symbol}
                for our_field, their_field in response_mapping.items():
                    val = data.get(their_field)
                    if val is not None:
                        try:
                            val = float(val.rstrip("%")) if isinstance(val, str) else float(val)
                        except (ValueError, TypeError, AttributeError):
                            pass
                    mapped[our_field] = val
                results.append(mapped)
            else:
                if symbol:
                    if isinstance(data, dict):
                        data["symbol"] = symbol
                results.append(data)

        return results if len(results) != 1 else results[0]

    # ── RSS ──────────────────────────────────────────────────────

    def _fetch_rss(self) -> list[dict]:
        """Fetch and parse an RSS feed."""
        try:
            import feedparser
        except ImportError:
            raise FetcherError("feedparser not installed. Run: pip install feedparser")

        url = self.config.get("url", "")
        max_items = self.config.get("max_items", 10)
        field_mapping = self.config.get("field_mapping", {
            "title": "title",
            "summary": "description",
            "url": "link",
        })

        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            raise FetcherError(f"RSS parse error: {feed.bozo_exception}")

        items = []
        for entry in feed.entries[:max_items]:
            item = {}
            for our_field, rss_field in field_mapping.items():
                item[our_field] = getattr(entry, rss_field, "") or entry.get(rss_field, "")
            items.append(item)

        return items

    # ── CSV ──────────────────────────────────────────────────────

    def _fetch_csv(self) -> list[dict]:
        """Read data from a local CSV file."""
        rel_path = self.config.get("path", "")
        csv_path = PROJECT_ROOT / rel_path
        if not csv_path.exists():
            raise FetcherError(f"CSV file not found: {csv_path}")

        columns = self.config.get("columns", {})
        rows = []

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                mapped = {}
                if columns:
                    for our_field, csv_col in columns.items():
                        val = row.get(csv_col, "")
                        # Auto-coerce numeric
                        try:
                            val = float(val.replace(",", "").replace("%", ""))
                        except (ValueError, AttributeError):
                            pass
                        mapped[our_field] = val
                else:
                    mapped = dict(row)
                rows.append(mapped)

        return rows
