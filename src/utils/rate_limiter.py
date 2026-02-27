"""Per-API rate limiting with call tracking."""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass

from src.utils.logging_config import get_logger

logger = get_logger("rate_limiter")


@dataclass
class APILimit:
    max_calls: int
    period_seconds: float  # Window size in seconds


# Default rate limits per API
DEFAULT_LIMITS: dict[str, APILimit] = {
    "twelvedata": APILimit(max_calls=7, period_seconds=60),     # 8/min API limit, buffer of 1
    "finnhub": APILimit(max_calls=55, period_seconds=60),       # 60/min with buffer
    "newsapi": APILimit(max_calls=90, period_seconds=86400),    # 100/day with buffer
    "fred": APILimit(max_calls=100, period_seconds=60),         # generous
    "yfinance": APILimit(max_calls=100, period_seconds=60),     # no official limit, generous
    "feargreed": APILimit(max_calls=5, period_seconds=300),     # scraping, be gentle
}


class RateLimiter:
    def __init__(self):
        self._calls: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def wait_if_needed(self, api_name: str) -> None:
        limit = DEFAULT_LIMITS.get(api_name)
        if not limit:
            return

        with self._lock:
            now = time.time()
            cutoff = now - limit.period_seconds
            # Prune old calls
            self._calls[api_name] = [t for t in self._calls[api_name] if t > cutoff]

            if len(self._calls[api_name]) >= limit.max_calls:
                oldest = self._calls[api_name][0]
                wait_time = oldest + limit.period_seconds - now + 0.1
                if wait_time > 0:
                    logger.info(f"Rate limit reached for {api_name}, waiting {wait_time:.1f}s")
                    time.sleep(wait_time)
                    # Prune again after wait
                    now = time.time()
                    cutoff = now - limit.period_seconds
                    self._calls[api_name] = [t for t in self._calls[api_name] if t > cutoff]

            self._calls[api_name].append(time.time())

    def get_remaining(self, api_name: str) -> int:
        limit = DEFAULT_LIMITS.get(api_name)
        if not limit:
            return 999

        with self._lock:
            now = time.time()
            cutoff = now - limit.period_seconds
            recent = [t for t in self._calls[api_name] if t > cutoff]
            return max(0, limit.max_calls - len(recent))


# Global instance
rate_limiter = RateLimiter()
