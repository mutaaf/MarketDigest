"""NewsAPI fetcher — headlines for sentiment scoring."""

from typing import Any

from newsapi import NewsApiClient

from config.settings import get_settings
from src.fetchers.base import BaseFetcher, FetcherError


class NewsAPIFetcher(BaseFetcher):
    def __init__(self):
        super().__init__()
        settings = get_settings()
        self._api_key = settings.api_keys.newsapi
        self._client: NewsApiClient | None = None

    @property
    def api_name(self) -> str:
        return "newsapi"

    @property
    def cache_ttl(self) -> int:
        return 1800  # 30 min — conserve 100/day limit

    @property
    def client(self) -> NewsApiClient:
        if self._client is None:
            if not self._api_key:
                raise FetcherError("NEWSAPI_KEY not configured")
            self._client = NewsApiClient(api_key=self._api_key)
        return self._client

    def get_market_headlines(self, query: str = "stock market OR forex OR economy", count: int = 20) -> list[dict[str, Any]]:
        """Get market-related news headlines."""

        def _fetch():
            data = self.client.get_everything(
                q=query,
                language="en",
                sort_by="publishedAt",
                page_size=count,
            )
            articles = data.get("articles", [])
            return [
                {
                    "title": a.get("title", ""),
                    "description": a.get("description", ""),
                    "source": a.get("source", {}).get("name", ""),
                    "published_at": a.get("publishedAt", ""),
                    "url": a.get("url", ""),
                }
                for a in articles
                if a.get("title") and a["title"] != "[Removed]"
            ]

        return self.fetch_with_cache("newsapi_market", _fetch) or []

    def get_top_business_headlines(self, count: int = 10) -> list[dict[str, Any]]:
        """Get top business headlines (uses different endpoint, counts separately)."""

        def _fetch():
            data = self.client.get_top_headlines(
                category="business",
                language="en",
                country="us",
                page_size=count,
            )
            articles = data.get("articles", [])
            return [
                {
                    "title": a.get("title", ""),
                    "description": a.get("description", ""),
                    "source": a.get("source", {}).get("name", ""),
                    "published_at": a.get("publishedAt", ""),
                }
                for a in articles
                if a.get("title") and a["title"] != "[Removed]"
            ]

        return self.fetch_with_cache("newsapi_business", _fetch) or []
