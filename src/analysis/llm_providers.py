"""LLM provider abstraction with lazy imports, auto-fallback, and caching."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml
from tenacity import retry, retry_if_exception_type, stop_after_attempt

from config.settings import get_settings
from src.cache.manager import cache
from src.utils.logging_config import get_logger

logger = get_logger("llm_providers")

LLM_CACHE_TTL = 7200  # 2 hours
PROMPTS_YAML = Path(__file__).parent.parent.parent / "config" / "prompts.yaml"

# Default fallback
_DEFAULT_PROVIDERS = [
    ("anthropic", "claude-haiku-4-5-20251001"),
    ("openai", "gpt-4o-mini"),
    ("gemini", "gemini-2.0-flash"),
]


def _load_provider_config() -> list[tuple[str, str]]:
    """Load provider priority and models from prompts.yaml."""
    try:
        if PROMPTS_YAML.exists():
            with open(PROMPTS_YAML) as f:
                config = yaml.safe_load(f) or {}
            priority = config.get("provider_priority")
            models = config.get("provider_models", {})
            if priority and models:
                default_models = {p: m for p, m in _DEFAULT_PROVIDERS}
                return [(p, models.get(p, default_models.get(p, ""))) for p in priority if models.get(p) or default_models.get(p)]
    except Exception as e:
        logger.warning(f"Failed to load provider config from YAML: {e}")
    return list(_DEFAULT_PROVIDERS)


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    tokens_used: int
    cached: bool


class LLMProvider:
    """Wraps Claude, OpenAI, and Gemini with priority fallback and caching."""

    def __init__(self):
        settings = get_settings()
        self._keys = settings.get_llm_keys_dict()
        self._clients: dict = {}
        self.PROVIDERS = _load_provider_config()

    def reload_config(self) -> None:
        """Reload provider priority and models from YAML."""
        self.PROVIDERS = _load_provider_config()

    def _get_client(self, provider: str):
        """Lazy-initialize and return a provider client."""
        if provider in self._clients:
            return self._clients[provider]

        key = self._keys.get(provider, "")
        if not key:
            return None

        client = None
        if provider == "anthropic":
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=key)
            except ImportError:
                logger.debug("anthropic SDK not installed, skipping")
            except Exception as e:
                logger.warning(f"Failed to init Anthropic client: {e}")

        elif provider == "openai":
            try:
                import openai
                client = openai.OpenAI(api_key=key)
            except ImportError:
                logger.debug("openai SDK not installed, skipping")
            except Exception as e:
                logger.warning(f"Failed to init OpenAI client: {e}")

        elif provider == "gemini":
            try:
                import google.generativeai as genai
                genai.configure(api_key=key)
                client = genai
            except ImportError:
                logger.debug("google-generativeai SDK not installed, skipping")
            except Exception as e:
                logger.warning(f"Failed to init Gemini client: {e}")

        if client:
            self._clients[provider] = client
        return client

    def _cache_key(self, system_prompt: str, user_prompt: str) -> str:
        content = system_prompt + user_prompt
        hash_val = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"llm_{hash_val}"

    @retry(stop=stop_after_attempt(2), retry=retry_if_exception_type(Exception), reraise=True)
    def _call_anthropic(self, client, model: str, system_prompt: str, user_prompt: str, max_tokens: int) -> LLMResponse:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = response.content[0].text
        tokens = response.usage.input_tokens + response.usage.output_tokens
        return LLMResponse(text=text, provider="anthropic", model=model, tokens_used=tokens, cached=False)

    @retry(stop=stop_after_attempt(2), retry=retry_if_exception_type(Exception), reraise=True)
    def _call_openai(self, client, model: str, system_prompt: str, user_prompt: str, max_tokens: int) -> LLMResponse:
        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else 0
        return LLMResponse(text=text, provider="openai", model=model, tokens_used=tokens, cached=False)

    @retry(stop=stop_after_attempt(2), retry=retry_if_exception_type(Exception), reraise=True)
    def _call_gemini(self, client, model: str, system_prompt: str, user_prompt: str, max_tokens: int) -> LLMResponse:
        gen_model = client.GenerativeModel(
            model_name=model,
            system_instruction=system_prompt,
            generation_config={"max_output_tokens": max_tokens},
        )
        response = gen_model.generate_content(user_prompt)
        text = response.text
        tokens = response.usage_metadata.total_token_count if hasattr(response, "usage_metadata") and response.usage_metadata else 0
        return LLMResponse(text=text, provider="gemini", model=model, tokens_used=tokens, cached=False)

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 400) -> LLMResponse | None:
        """Generate text using first available provider, with caching."""
        # Check cache first
        key = self._cache_key(system_prompt, user_prompt)
        cached = cache.get(key, max_age_seconds=LLM_CACHE_TTL)
        if cached:
            logger.info("LLM cache hit")
            return LLMResponse(
                text=cached["text"],
                provider=cached["provider"],
                model=cached["model"],
                tokens_used=cached["tokens_used"],
                cached=True,
            )

        # Try each provider in priority order
        last_error = None
        for provider_name, model in self.PROVIDERS:
            client = self._get_client(provider_name)
            if client is None:
                continue

            try:
                logger.info(f"Calling LLM: {provider_name}/{model}")
                if provider_name == "anthropic":
                    result = self._call_anthropic(client, model, system_prompt, user_prompt, max_tokens)
                elif provider_name == "openai":
                    result = self._call_openai(client, model, system_prompt, user_prompt, max_tokens)
                elif provider_name == "gemini":
                    result = self._call_gemini(client, model, system_prompt, user_prompt, max_tokens)
                else:
                    continue

                # Cache the result
                cache.set(key, {
                    "text": result.text,
                    "provider": result.provider,
                    "model": result.model,
                    "tokens_used": result.tokens_used,
                }, persist=True)

                return result

            except Exception as e:
                last_error = e
                logger.warning(f"LLM call failed ({provider_name}): {e}")
                continue

        # All providers failed — try stale cache as last resort
        stale = cache.get_stale(key)
        if stale:
            logger.info("Using stale LLM cache after all providers failed")
            return LLMResponse(
                text=stale["text"],
                provider=stale["provider"],
                model=stale["model"],
                tokens_used=stale["tokens_used"],
                cached=True,
            )

        logger.error(f"All LLM providers failed. Last error: {last_error}")
        return None
