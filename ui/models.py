"""Pydantic request/response models for the UI API."""

from pydantic import BaseModel


class ApiKeyUpdate(BaseModel):
    key: str
    value: str


class ApiTestResult(BaseModel):
    api: str
    success: bool
    message: str


class InstrumentToggle(BaseModel):
    enabled: bool


class NewInstrument(BaseModel):
    symbol: str
    yfinance: str
    name: str
    category: str
    subcategory: str | None = None
    twelvedata: str | None = None


class PromptUpdate(BaseModel):
    prompt: str
    max_tokens: int | None = None
    include_cross_context: bool | None = None


class SystemPromptUpdate(BaseModel):
    system_prompt: str


class LLMProviderConfig(BaseModel):
    provider_priority: list[str]
    provider_models: dict[str, str]


class DigestRunRequest(BaseModel):
    digest_type: str
    mode: str = "facts"
    dry_run: bool = True
    action_items: bool = False


class DigestSendRequest(BaseModel):
    content: str


class DigestConfigUpdate(BaseModel):
    sections: list[str] | None = None
    default_mode: str | None = None
    schedule: str | None = None


class SettingsUpdate(BaseModel):
    timezone: str | None = None
    log_level: str | None = None


class RecipientAdd(BaseModel):
    chat_id: str
    label: str = ""


class SourceToggle(BaseModel):
    enabled: bool


class ScoringWeightsUpdate(BaseModel):
    weights: dict[str, float]
    description: str = ""


class RollbackRequest(BaseModel):
    config_name: str
    version_id: str
