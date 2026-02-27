"""Test config loading."""

from config.settings import Settings


def test_settings_defaults():
    """Settings should have sensible defaults when no .env is loaded."""
    s = Settings()
    assert s.timezone == "US/Central"
    assert s.log_level == "INFO"
    assert s.telegram.bot_token == ""
    assert s.api_keys.twelvedata == ""
    assert s.llm_keys.anthropic == ""


def test_settings_instruments_default_empty():
    """Instruments dict should be empty by default."""
    s = Settings()
    assert s.instruments == {}
