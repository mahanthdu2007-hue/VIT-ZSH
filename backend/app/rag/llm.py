"""§3 one interface over the System 2 generators: Gemini, NVIDIA NIM and none.

Callers use `complete_json(system, user, schema)` and `complete_text(system, user)`. Every failure raises a
subclass of `LLMError`, which callers turn into deterministic template fallbacks. LLMs never compute numbers.
"""

import json
import re
import time
from collections.abc import Callable
from functools import lru_cache
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ValidationError

from app.engine import config
from app.settings import Settings, get_settings

ProviderName = Literal["gemini", "nvidia", "none"]
Sleep = Callable[[float], None]


class LLMError(Exception):
    """Base for every System 2 generator failure."""


class LLMNotConfigured(LLMError):
    """No provider is active (LLM_PROVIDER=none, or no key / model)."""


class LLMTimeout(LLMError):
    """The provider did not answer within the timeout."""


class LLMRateLimited(LLMError):
    """HTTP 429, or 503 (provider busy): retried once after a wait, then raised."""


class LLMUnavailable(LLMError):
    """Any other API or network error."""


class LLMBadResponse(LLMError):
    """Empty text, or JSON that does not parse or does not match the schema."""


class LLMStatus(BaseModel):
    """What /api/health reports about System 2."""
    requested: Literal["auto", "gemini", "nvidia", "none"]
    provider: ProviderName
    model: str | None
    notes: list[str]


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")


def parse_json_object(text: str) -> dict[str, Any]:
    """The first JSON object in `text`, tolerating code fences and prose around it."""
    cleaned = _FENCE.sub("", text.strip())
    candidates = [cleaned]
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if 0 <= start < end:
        candidates.append(cleaned[start:end + 1])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise LLMBadResponse("reply is not a JSON object")


def _json_instruction(schema: type[BaseModel]) -> str:
    return ("\n\nReply with exactly one JSON object and nothing else. It must match this JSON schema:\n"
            + json.dumps(schema.model_json_schema(), separators=(",", ":")))


class Provider:
    """Shared retry, JSON and error handling; subclasses implement `_call`."""
    name: ProviderName = "none"

    def __init__(self, model: str | None, sleep: Sleep = time.sleep) -> None:
        self.model = model
        self._sleep = sleep

    def _call(self, system: str, user: str, json_mode: bool, timeout_s: float) -> str:
        raise LLMNotConfigured("no LLM provider is active")

    def _generate(self, system: str, user: str, json_mode: bool, timeout_s: float) -> str:
        try:
            text = self._call(system, user, json_mode, timeout_s)
        except LLMRateLimited:
            self._sleep(config.LLM_RATE_LIMIT_WAIT_S)
            text = self._call(system, user, json_mode, timeout_s)
        if not text.strip():
            raise LLMBadResponse("empty reply")
        return text.strip()

    def complete_text(self, system: str, user: str, timeout_s: float = config.LLM_TIMEOUT_S) -> str:
        return self._generate(system, user, False, timeout_s)

    def complete_json(self, system: str, user: str, schema: type[BaseModel],
                      timeout_s: float = config.LLM_TIMEOUT_S) -> dict[str, Any]:
        raw = self._generate(system + _json_instruction(schema), user, True, timeout_s)
        try:
            return schema.model_validate(parse_json_object(raw)).model_dump()
        except ValidationError as error:
            raise LLMBadResponse(f"JSON does not match {schema.__name__}") from error

    def probe(self) -> None:
        """§3 auto mode: a tiny request that must succeed for this provider to be chosen."""
        self.complete_text("Reply with the single word OK.", "Ping", timeout_s=config.LLM_PROBE_TIMEOUT_S)


class NoneProvider(Provider):
    """§3 `none`: deterministic templates only; every call raises LLMNotConfigured."""
    name: ProviderName = "none"

    def __init__(self) -> None:
        super().__init__(None)


class GeminiProvider(Provider):
    """§3 Gemini through the google-genai SDK."""
    name: ProviderName = "gemini"

    def __init__(self, api_key: str, model: str, client: Any = None, sleep: Sleep = time.sleep) -> None:
        super().__init__(model, sleep)
        if client is None:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=api_key,
                                  http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1)))
        self._client = client

    def _call(self, system: str, user: str, json_mode: bool, timeout_s: float) -> str:
        from google.genai import errors, types
        generation = types.GenerateContentConfig(
            system_instruction=system,
            temperature=config.LLM_TEMPERATURE,
            max_output_tokens=config.LLM_MAX_TOKENS,
            response_mime_type="application/json" if json_mode else None,
            thinking_config=types.ThinkingConfig(thinking_level=config.GEMINI_THINKING_LEVEL),
            http_options=types.HttpOptions(timeout=int(timeout_s * 1000)),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        try:
            response = self._client.models.generate_content(model=self.model, contents=user, config=generation)
        except errors.APIError as error:
            if error.code in config.LLM_BUSY_STATUS_CODES:
                raise LLMRateLimited(f"Gemini HTTP {error.code}") from error
            if error.code == 504:
                raise LLMTimeout(str(error)) from error
            raise LLMUnavailable(f"Gemini HTTP {error.code}") from error
        except httpx.TimeoutException as error:
            raise LLMTimeout("Gemini timed out") from error
        except httpx.HTTPError as error:
            raise LLMUnavailable(f"Gemini network error: {type(error).__name__}") from error
        return response.text or ""


class NvidiaProvider(Provider):
    """§3 NVIDIA NIM through the openai SDK. Only the final message content is used, never the reasoning."""
    name: ProviderName = "nvidia"

    def __init__(self, api_key: str, model: str, client: Any = None, sleep: Sleep = time.sleep) -> None:
        super().__init__(model, sleep)
        if client is None:
            from openai import OpenAI
            client = OpenAI(base_url=config.NVIDIA_BASE_URL, api_key=api_key, max_retries=0)
        self._client = client

    def _request(self, system: str, user: str, max_tokens: int, timeout_s: float) -> str:
        import openai
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=config.LLM_TEMPERATURE, max_tokens=max_tokens, timeout=timeout_s,
                extra_body=config.NVIDIA_EXTRA_BODY)
        except openai.APIStatusError as error:
            if error.status_code in config.LLM_BUSY_STATUS_CODES:
                raise LLMRateLimited(f"NVIDIA HTTP {error.status_code}") from error
            raise LLMUnavailable(f"NVIDIA HTTP {error.status_code}") from error
        except openai.APITimeoutError as error:
            raise LLMTimeout("NVIDIA timed out") from error
        except openai.APIError as error:
            raise LLMUnavailable(f"NVIDIA error: {type(error).__name__}") from error
        return response.choices[0].message.content or ""

    def _call(self, system: str, user: str, json_mode: bool, timeout_s: float) -> str:
        text = self._request(system, user, config.LLM_MAX_TOKENS, timeout_s)
        if not text.strip():  # §3 the budget went on reasoning: retry once with more room
            text = self._request(system, user, config.LLM_EMPTY_RETRY_MAX_TOKENS, timeout_s)
        return text


ProviderFactory = Callable[[Settings], Provider]
FACTORIES: dict[str, ProviderFactory] = {
    "gemini": lambda s: GeminiProvider(s.gemini_api_key, s.gemini_model),
    "nvidia": lambda s: NvidiaProvider(s.nvidia_api_key, s.nvidia_model),
}


def _configured(name: str, settings: Settings) -> bool:
    return bool(getattr(settings, f"{name}_api_key") and getattr(settings, f"{name}_model"))


def select_provider(settings: Settings,
                    factories: dict[str, ProviderFactory] = FACTORIES) -> tuple[Provider, LLMStatus]:
    """§3 the active provider. `auto` tests Gemini, then NVIDIA, with a tiny request; else `none`."""
    requested = settings.llm_provider
    notes: list[str] = []
    provider: Provider = NoneProvider()
    if requested in factories:
        if _configured(requested, settings):
            provider = factories[requested](settings)
        else:
            notes.append(f"{requested}: key or model missing")
    elif requested == "auto":
        for name in config.LLM_PROVIDER_ORDER:
            if not _configured(name, settings):
                notes.append(f"{name}: key or model missing")
                continue
            candidate = factories[name](settings)
            try:
                candidate.probe()
            except LLMError as error:
                notes.append(f"{name}: test failed ({type(error).__name__})")
                continue
            provider = candidate
            break
    return provider, LLMStatus(requested=requested, provider=provider.name, model=provider.model, notes=notes)


@lru_cache
def _active() -> tuple[Provider, LLMStatus]:
    return select_provider(get_settings())


def get_llm() -> Provider:
    return _active()[0]


def llm_status() -> LLMStatus:
    return _active()[1]


def complete_json(system: str, user: str, schema: type[BaseModel]) -> dict[str, Any]:
    return get_llm().complete_json(system, user, schema)


def complete_text(system: str, user: str) -> str:
    return get_llm().complete_text(system, user)
