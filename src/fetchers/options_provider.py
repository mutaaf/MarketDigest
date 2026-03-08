"""Multi-provider options data orchestrator — merge yfinance + UW + AV data."""

from typing import Any

from src.utils.logging_config import get_logger

logger = get_logger("options_provider")


class OptionsDataProvider:
    """Orchestrates data from multiple options providers (complementary, not fallback)."""

    def __init__(self):
        self._yf = None
        self._uw = None
        self._av = None
        self._init_providers()

    def _init_providers(self):
        try:
            from src.fetchers.options_fetcher import OptionsFetcher
            self._yf = OptionsFetcher()
        except Exception as e:
            logger.warning(f"Failed to init yfinance options: {e}")

        try:
            from src.fetchers.uw_fetcher import UnusualWhalesFetcher
            uw = UnusualWhalesFetcher()
            if uw.available:
                self._uw = uw
        except Exception as e:
            logger.debug(f"UW not available: {e}")

        try:
            from src.fetchers.av_options_fetcher import AlphaVantageOptionsFetcher
            av = AlphaVantageOptionsFetcher()
            if av.available:
                self._av = av
        except Exception as e:
            logger.debug(f"AV not available: {e}")

    def get_provider_status(self) -> dict:
        """Return which providers are configured and active."""
        return {
            "yfinance": self._yf is not None,
            "unusual_whales": self._uw is not None,
            "alpha_vantage": self._av is not None,
        }

    def get_enriched_data(self, symbol: str) -> dict:
        """Fetch and merge data from all available providers."""
        # Chain data: yfinance primary, AV fallback
        chain_data = None
        chain_provider = None
        if self._yf:
            chain_data = self._yf.get_option_chain(symbol)
            if chain_data:
                chain_provider = "yfinance"

        if chain_data is None and self._av:
            chain_data = self._av.get_historical_chain(symbol)
            if chain_data:
                chain_provider = "alpha_vantage"

        if chain_data is None:
            return {"error": f"No options data available for {symbol}"}

        # Flow alerts from UW
        flow_alerts = self._uw.get_flow_alerts(symbol) if self._uw else None

        # Dark pool from UW
        dark_pool = self._uw.get_dark_pool_prints(symbol) if self._uw else None

        # Institutional activity from UW
        institutional = self._uw.get_institutional_activity(symbol) if self._uw else None

        # Flow intervals from UW
        flow_intervals = self._uw.get_flow_intervals(symbol) if self._uw else None

        # Historical IV from AV
        historical_iv = self._av.get_historical_iv(symbol) if self._av else None

        return {
            "chain_data": chain_data,
            "chain_provider": chain_provider,
            "flow_alerts": flow_alerts,
            "dark_pool": dark_pool,
            "institutional": institutional,
            "flow_intervals": flow_intervals,
            "historical_iv": historical_iv,
            "provider_status": self.get_provider_status(),
        }

    def get_flow_alerts_only(self, symbol: str) -> list[dict]:
        """Lightweight sweep alert polling."""
        if self._uw:
            return self._uw.get_flow_alerts(symbol, limit=30)
        return []
