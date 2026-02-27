"""CNN Fear & Greed Index fetcher."""

from typing import Any

import requests

from src.fetchers.base import BaseFetcher


class FearGreedFetcher(BaseFetcher):
    CNN_FG_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"

    @property
    def api_name(self) -> str:
        return "feargreed"

    @property
    def cache_ttl(self) -> int:
        return 1800  # 30 min

    def get_fear_greed_index(self) -> dict[str, Any] | None:
        """Get CNN Fear & Greed Index score and classification."""

        def _fetch():
            # Try CNN API endpoint first
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                }
                resp = requests.get(self.CNN_FG_URL, headers=headers, timeout=10)
                resp.raise_for_status()
                data = resp.json()

                fg = data.get("fear_and_greed", {})
                score = fg.get("score", 0)
                rating = fg.get("rating", "")
                prev_close = fg.get("previous_close", 0)
                prev_week = data.get("fear_and_greed_historical", {}).get("one_week_ago", {}).get("score", 0)

                return {
                    "score": round(float(score)),
                    "rating": rating,
                    "prev_close": round(float(prev_close)) if prev_close else None,
                    "prev_week": round(float(prev_week)) if prev_week else None,
                    "classification": self._classify(float(score)),
                }
            except Exception as e:
                self.logger.warning(f"CNN F&G API failed: {e}")

            # Fallback: try fear-greed-index package
            try:
                from fear_greed_index import get as fg_get
                data = fg_get()
                score = float(data.get("score", 50))
                return {
                    "score": round(score),
                    "rating": data.get("description", ""),
                    "prev_close": None,
                    "prev_week": None,
                    "classification": self._classify(score),
                }
            except (ImportError, Exception) as e:
                self.logger.warning(f"fear-greed-index fallback failed: {e}")
                return None

        return self.fetch_with_cache("fear_greed_index", _fetch)

    @staticmethod
    def _classify(score: float) -> str:
        if score <= 25:
            return "Extreme Fear"
        elif score <= 45:
            return "Fear"
        elif score <= 55:
            return "Neutral"
        elif score <= 75:
            return "Greed"
        else:
            return "Extreme Greed"
