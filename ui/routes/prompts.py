"""Prompts management endpoints."""


import yaml
from fastapi import APIRouter, HTTPException

from config.settings import PROJECT_ROOT
from src.analysis.llm_analyzer import (
    _DEFAULT_PROMPTS,
    _DEFAULT_SYSTEM_PROMPT,
    _DEFAULT_TOKEN_OVERRIDES,
    DEFAULT_MAX_TOKENS,
    reload_prompts,
)
from ui.models import LLMProviderConfig, PromptUpdate, SystemPromptUpdate

router = APIRouter(prefix="/api/prompts", tags=["prompts"])

PROMPTS_YAML = PROJECT_ROOT / "config" / "prompts.yaml"


def _load_prompts_yaml() -> dict:
    if PROMPTS_YAML.exists():
        with open(PROMPTS_YAML) as f:
            return yaml.safe_load(f) or {}
    return {}


def _save_prompts_yaml(config: dict, description: str = "Prompts updated") -> None:
    with open(PROMPTS_YAML, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    reload_prompts()
    try:
        from src.retrace.versioning import save_version
        save_version("prompts", config, description)
    except Exception:
        pass


@router.get("")
def get_prompts():
    """Get all prompt configuration."""
    config = _load_prompts_yaml()

    sections = {}
    all_section_names = list(_DEFAULT_PROMPTS.keys())

    for name in all_section_names:
        yaml_section = config.get("sections", {}).get(name, {})
        sections[name] = {
            "prompt": yaml_section.get("prompt", _DEFAULT_PROMPTS.get(name, "")),
            "max_tokens": yaml_section.get("max_tokens", _DEFAULT_TOKEN_OVERRIDES.get(name, config.get("default_max_tokens", DEFAULT_MAX_TOKENS))),
            "include_cross_context": yaml_section.get("include_cross_context", True),
            "is_default": "prompt" not in yaml_section,
        }

    return {
        "system_prompt": config.get("system_prompt", _DEFAULT_SYSTEM_PROMPT),
        "default_max_tokens": config.get("default_max_tokens", DEFAULT_MAX_TOKENS),
        "sections": sections,
        "section_names": all_section_names,
    }


@router.put("/system")
def update_system_prompt(body: SystemPromptUpdate):
    """Update the system prompt."""
    config = _load_prompts_yaml()
    config["system_prompt"] = body.system_prompt
    _save_prompts_yaml(config, "System prompt updated")
    return {"success": True}


@router.put("/sections/{section_name}")
def update_section_prompt(section_name: str, body: PromptUpdate):
    """Update a single section prompt."""
    if section_name not in _DEFAULT_PROMPTS:
        raise HTTPException(status_code=404, detail=f"Unknown section: {section_name}")

    config = _load_prompts_yaml()
    if "sections" not in config:
        config["sections"] = {}
    if section_name not in config["sections"]:
        config["sections"][section_name] = {}

    config["sections"][section_name]["prompt"] = body.prompt
    if body.max_tokens is not None:
        config["sections"][section_name]["max_tokens"] = body.max_tokens
    if body.include_cross_context is not None:
        config["sections"][section_name]["include_cross_context"] = body.include_cross_context

    _save_prompts_yaml(config, f"Section '{section_name}' updated")
    return {"success": True}


@router.post("/reset/{section_name}")
def reset_section_prompt(section_name: str):
    """Reset a section prompt to default."""
    if section_name not in _DEFAULT_PROMPTS:
        raise HTTPException(status_code=404, detail=f"Unknown section: {section_name}")

    config = _load_prompts_yaml()
    if "sections" in config and section_name in config["sections"]:
        del config["sections"][section_name]
        _save_prompts_yaml(config, f"Section '{section_name}' reset to default")

    return {"success": True, "prompt": _DEFAULT_PROMPTS[section_name]}


@router.post("/reset-all")
def reset_all_prompts():
    """Reset all prompts to defaults."""
    config = _load_prompts_yaml()
    config["system_prompt"] = _DEFAULT_SYSTEM_PROMPT
    config["sections"] = {}
    _save_prompts_yaml(config, "All prompts reset to defaults")
    return {"success": True}


@router.get("/llm-config")
def get_llm_config():
    """Get LLM provider priority and models."""
    config = _load_prompts_yaml()
    return {
        "provider_priority": config.get("provider_priority", ["anthropic", "openai", "gemini"]),
        "provider_models": config.get("provider_models", {
            "anthropic": "claude-haiku-4-5-20251001",
            "openai": "gpt-4o-mini",
            "gemini": "gemini-2.0-flash",
        }),
    }


@router.put("/llm-config")
def update_llm_config(body: LLMProviderConfig):
    """Update LLM provider priority and models."""
    config = _load_prompts_yaml()
    config["provider_priority"] = body.provider_priority
    config["provider_models"] = body.provider_models
    _save_prompts_yaml(config, "LLM config updated")
    return {"success": True}
