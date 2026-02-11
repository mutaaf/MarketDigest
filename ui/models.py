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


class CustomSourceAuth(BaseModel):
    type: str = "none"  # api_key | bearer | header | none
    env_var: str | None = None
    header_name: str | None = None


class CustomSourceDigestIntegration(BaseModel):
    mode: str = "section"  # section | merge
    merge_target: str | None = None
    section_title: str = ""
    digest_types: list[str] = []


class CustomSourceCreate(BaseModel):
    name: str
    type: str  # http | rss | csv
    enabled: bool = True
    url: str | None = None
    path: str | None = None
    auth: CustomSourceAuth | None = None
    response_root: str | None = None
    response_mapping: dict[str, str] | None = None
    instruments: list[str] | None = None
    field_mapping: dict[str, str] | None = None
    columns: dict[str, str] | None = None
    max_items: int | None = None
    cache_ttl: int = 300
    digest_integration: CustomSourceDigestIntegration | None = None


class CustomSourceUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    enabled: bool | None = None
    url: str | None = None
    path: str | None = None
    auth: CustomSourceAuth | None = None
    response_root: str | None = None
    response_mapping: dict[str, str] | None = None
    instruments: list[str] | None = None
    field_mapping: dict[str, str] | None = None
    columns: dict[str, str] | None = None
    max_items: int | None = None
    cache_ttl: int | None = None
    digest_integration: CustomSourceDigestIntegration | None = None
