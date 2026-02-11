"""Dataclass-based configuration, loads from .env and instruments.yaml."""

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).parent.parent


@dataclass
class TelegramConfig:
    bot_token: str = ""
    _chat_ids: list[str] = field(default_factory=list)
    _chat_labels: dict[str, str] = field(default_factory=dict)

    @property
    def chat_id(self) -> str:
        """Backward compat: return first chat ID."""
        return self._chat_ids[0] if self._chat_ids else ""

    @property
    def chat_ids(self) -> list[str]:
        return self._chat_ids

    @property
    def chat_labels(self) -> dict[str, str]:
        return self._chat_labels


@dataclass
class APIKeys:
    twelvedata: str = ""
    finnhub: str = ""
    fred: str = ""
    newsapi: str = ""


@dataclass
class LLMKeys:
    anthropic: str = ""
    openai: str = ""
    gemini: str = ""


@dataclass
class Settings:
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    api_keys: APIKeys = field(default_factory=APIKeys)
    llm_keys: LLMKeys = field(default_factory=LLMKeys)
    timezone: str = "US/Central"
    log_level: str = "INFO"
    project_root: Path = PROJECT_ROOT
    instruments: dict[str, Any] = field(default_factory=dict)

    @property
    def cache_dir(self) -> Path:
        return self.project_root / "cache"

    @property
    def logs_dir(self) -> Path:
        return self.project_root / "logs"

    def has_api_key(self, name: str) -> bool:
        return bool(getattr(self.api_keys, name, ""))

    def has_llm_key(self) -> bool:
        return bool(self.llm_keys.anthropic or self.llm_keys.openai or self.llm_keys.gemini)

    def get_llm_keys_dict(self) -> dict[str, str]:
        return {
            "anthropic": self.llm_keys.anthropic,
            "openai": self.llm_keys.openai,
            "gemini": self.llm_keys.gemini,
        }


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = _load_settings()
    return _settings


def reload_settings() -> Settings:
    """Clear singleton and force re-read from .env and instruments.yaml."""
    global _settings
    _settings = None
    return get_settings()


def _load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env", override=True)

    instruments = _load_instruments()

    # Parse comma-separated chat IDs and labels
    raw_ids = os.getenv("TELEGRAM_CHAT_ID", "")
    chat_ids = [cid.strip() for cid in raw_ids.split(",") if cid.strip()] if raw_ids else []
    raw_labels = os.getenv("TELEGRAM_CHAT_LABELS", "")
    label_list = [lbl.strip() for lbl in raw_labels.split(",")]  if raw_labels else []
    chat_labels = {chat_ids[i]: label_list[i] for i in range(min(len(chat_ids), len(label_list))) if label_list[i]}

    return Settings(
        telegram=TelegramConfig(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            _chat_ids=chat_ids,
            _chat_labels=chat_labels,
        ),
        api_keys=APIKeys(
            twelvedata=os.getenv("TWELVEDATA_API_KEY", ""),
            finnhub=os.getenv("FINNHUB_API_KEY", ""),
            fred=os.getenv("FRED_API_KEY", ""),
            newsapi=os.getenv("NEWSAPI_KEY", ""),
        ),
        llm_keys=LLMKeys(
            anthropic=os.getenv("ANTHROPIC_API_KEY", ""),
            openai=os.getenv("OPENAI_API_KEY", ""),
            gemini=os.getenv("GEMINI_API_KEY", ""),
        ),
        timezone=os.getenv("TIMEZONE", "US/Central"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        instruments=instruments,
    )


def _load_instruments() -> dict[str, Any]:
    yaml_path = PROJECT_ROOT / "config" / "instruments.yaml"
    with open(yaml_path) as f:
        return yaml.safe_load(f)


def get_all_yfinance_tickers() -> list[dict[str, str]]:
    """Return flat list of {symbol, yfinance, name, category} for enabled instruments."""
    settings = get_settings()
    instruments = settings.instruments
    tickers = []

    # Forex
    for pair in instruments.get("forex", {}).get("majors", []):
        if pair.get("enabled", True):
            tickers.append({**pair, "category": "forex"})
    for idx in instruments.get("forex", {}).get("indices", []):
        if idx.get("enabled", True):
            tickers.append({**idx, "category": "forex_index"})

    # US Indices
    for item in instruments.get("us_indices", {}).get("spot", []):
        if item.get("enabled", True):
            tickers.append({**item, "category": "us_index"})
    for item in instruments.get("us_indices", {}).get("futures", []):
        if item.get("enabled", True):
            tickers.append({**item, "category": "us_futures"})

    # Commodities
    for sub in ["metals", "energy", "agriculture"]:
        for item in instruments.get("commodities", {}).get(sub, []):
            if item.get("enabled", True):
                tickers.append({**item, "category": sub})

    # Crypto
    for item in instruments.get("crypto", []):
        if item.get("enabled", True):
            tickers.append({**item, "category": "crypto"})

    # US Stocks (day-trade universe)
    for item in instruments.get("us_stocks", []):
        if item.get("enabled", True):
            tickers.append({**item, "category": "us_stock"})

    return tickers


# ── Write-back helpers ──────────────────────────────────────────


def get_env_var(key: str) -> str | None:
    """Read a raw value from the .env file for display."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        k, _, v = stripped.partition("=")
        if k.strip() == key:
            return v.strip()
    return None


def update_env_var(key: str, value: str) -> None:
    """Line-by-line .env editor: replace existing, uncomment, or append."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        env_path.write_text(f"{key}={value}\n")
        os.environ[key] = value
        return

    lines = env_path.read_text().splitlines()
    found = False
    new_lines = []

    for line in lines:
        stripped = line.strip()
        # Match active line: KEY=...
        if not stripped.startswith("#") and "=" in stripped:
            k, _, _ = stripped.partition("=")
            if k.strip() == key:
                new_lines.append(f"{key}={value}")
                found = True
                continue
        # Match commented line: # KEY=...
        if stripped.startswith("#"):
            uncommented = stripped.lstrip("# ")
            if "=" in uncommented:
                k, _, _ = uncommented.partition("=")
                if k.strip() == key:
                    new_lines.append(f"{key}={value}")
                    found = True
                    continue
        new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}")

    env_path.write_text("\n".join(new_lines) + "\n")
    os.environ[key] = value


def add_chat_id(chat_id: str, label: str = "") -> None:
    """Add a Telegram chat ID (and optional label) to .env, then reload."""
    settings = get_settings()
    ids = list(settings.telegram.chat_ids)
    labels = dict(settings.telegram.chat_labels)
    if chat_id in ids:
        # Update label only
        if label:
            labels[chat_id] = label
        elif chat_id in labels:
            del labels[chat_id]
    else:
        ids.append(chat_id)
        if label:
            labels[chat_id] = label

    _write_chat_ids(ids, labels)
    reload_settings()


def remove_chat_id(chat_id: str) -> None:
    """Remove a Telegram chat ID from .env, then reload."""
    settings = get_settings()
    ids = [cid for cid in settings.telegram.chat_ids if cid != chat_id]
    labels = {k: v for k, v in settings.telegram.chat_labels.items() if k != chat_id}
    _write_chat_ids(ids, labels)
    reload_settings()


def _write_chat_ids(ids: list[str], labels: dict[str, str]) -> None:
    """Persist chat IDs and labels to .env."""
    update_env_var("TELEGRAM_CHAT_ID", ",".join(ids))
    # Build parallel label list (empty string for unlabelled)
    label_list = [labels.get(cid, "") for cid in ids]
    update_env_var("TELEGRAM_CHAT_LABELS", ",".join(label_list))


def save_instruments(instruments: dict[str, Any]) -> None:
    """Atomic write of instruments.yaml via tempfile + os.replace()."""
    yaml_path = PROJECT_ROOT / "config" / "instruments.yaml"
    fd, tmp_path = tempfile.mkstemp(dir=yaml_path.parent, suffix=".yaml")
    try:
        with os.fdopen(fd, "w") as f:
            yaml.dump(instruments, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        os.replace(tmp_path, yaml_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
