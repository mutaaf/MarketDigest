"""Abstract base fetcher with retry, caching, and error handling."""

from abc import ABC, abstractmethod
from typing import Any

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.cache.manager import cache
from src.utils.logging_config import get_logger
from src.utils.rate_limiter import rate_limiter


class FetcherError(Exception):
    """Base exception for fetcher errors."""
    pass


class BaseFetcher(ABC):
    """Abstract base class for all data fetchers."""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.cache = cache
        self.rate_limiter = rate_limiter

    @property
    @abstractmethod
    def api_name(self) -> str:
        """Name used for rate limiting and logging."""
        ...

    @property
    def cache_ttl(self) -> int:
        """Default cache TTL in seconds. Override per fetcher."""
        return 300  # 5 minutes

    def fetch_with_cache(self, cache_key: str, fetch_fn, ttl: int | None = None, **kwargs) -> Any:
        """Fetch data with cache check, rate limiting, and error handling."""
        ttl = ttl or self.cache_ttl

        # Check fresh cache
        cached = self.cache.get(cache_key, max_age_seconds=ttl)
        if cached is not None:
            self.logger.debug(f"Cache hit: {cache_key}")
            return cached

        try:
            self.rate_limiter.wait_if_needed(self.api_name)
            data = fetch_fn(**kwargs)
            if data is not None:
                self.cache.set(cache_key, data)
            return data
        except Exception as e:
            self.logger.warning(f"Fetch failed for {cache_key}: {e}")
            # Try stale cache
            stale = self.cache.get_stale(cache_key)
            if stale is not None:
                self.logger.info(f"Using stale cache for {cache_key}")
                return stale
            raise FetcherError(f"Failed to fetch {cache_key}: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True,
    )
    def _retry_request(self, fn, *args, **kwargs) -> Any:
        """Execute a function with retry logic."""
        return fn(*args, **kwargs)
