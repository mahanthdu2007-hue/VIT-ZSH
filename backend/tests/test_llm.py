"""§3 rag/llm.py with mocked Gemini and NVIDIA clients: no network calls."""

from types import SimpleNamespace
from typing import Any

import httpx
import openai
import pytest
from google.genai import errors as genai_errors
from pydantic import BaseModel

from app.engine import config
from app.rag.llm import (
    GeminiProvider,
    LLMBadResponse,
    LLMNotConfigured,
    LLMRateLimited,
    LLMTimeout,
    LLMUnavailable,
    NoneProvider,
    NvidiaProvider,
    Provider,
    parse_json_object,
    select_provider,
)
from app.settings import Settings

NVIDIA_REQUEST = httpx.Request("POST", f"{config.NVIDIA_BASE_URL}/chat/completions")


class Reply(BaseModel):
    ok: bool


class FakeGeminiModels:
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = outcomes
        self.calls: list[dict[str, Any]] = []

    def generate_content(self, model: str, contents: str, config: Any) -> Any:
        self.calls.append({"model": model, "contents": contents, "config": config})
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(text=outcome)


class FakeNvidiaCompletions:
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = outcomes
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        message = SimpleNamespace(content=outcome, reasoning_content="private thinking that must never be used")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def gemini(outcomes: list[Any]) -> tuple[GeminiProvider, FakeGeminiModels, list[float]]:
    models = FakeGeminiModels(outcomes)
    waits: list[float] = []
    return GeminiProvider("key", "gemini-test", client=SimpleNamespace(models=models), sleep=waits.append), models, waits


def nvidia(outcomes: list[Any]) -> tuple[NvidiaProvider, FakeNvidiaCompletions, list[float]]:
    completions = FakeNvidiaCompletions(outcomes)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    waits: list[float] = []
    return NvidiaProvider("key", "nemotron-test", client=client, sleep=waits.append), completions, waits


def gemini_error(code: int) -> genai_errors.APIError:
    cls = genai_errors.ClientError if code < 500 else genai_errors.ServerError
    return cls(code, {"error": {"code": code, "message": "x", "status": "x"}})


def nvidia_rate_limit() -> openai.RateLimitError:
    return openai.RateLimitError("slow down", response=httpx.Response(429, request=NVIDIA_REQUEST), body=None)


# ---------------------------------------------------------------- JSON parsing
@pytest.mark.parametrize("text", ['{"ok": true}', '```json\n{"ok": true}\n```', 'Sure! {"ok": true} Hope it helps.'])
def test_parse_json_object_tolerates_fences_and_prose(text: str) -> None:
    assert parse_json_object(text) == {"ok": True}


@pytest.mark.parametrize("text", ["not json", "[1, 2]", "{broken"])
def test_parse_json_object_rejects_non_objects(text: str) -> None:
    with pytest.raises(LLMBadResponse):
        parse_json_object(text)


# ---------------------------------------------------------------- Gemini
def test_gemini_text_and_json() -> None:
    provider, models, _ = gemini(["Hello there", '{"ok": true}'])
    assert provider.complete_text("sys", "hi") == "Hello there"
    assert provider.complete_json("sys", "hi", Reply) == {"ok": True}
    sent = models.calls[1]["config"]
    assert models.calls[1]["model"] == "gemini-test"
    assert sent.temperature == config.LLM_TEMPERATURE
    assert sent.response_mime_type == "application/json"
    assert "JSON schema" in sent.system_instruction
    assert sent.thinking_config.thinking_level.value.lower() == config.GEMINI_THINKING_LEVEL


def test_gemini_retries_once_on_429_then_succeeds() -> None:
    provider, models, waits = gemini([gemini_error(429), "OK"])
    assert provider.complete_text("sys", "hi") == "OK"
    assert waits == [config.LLM_RATE_LIMIT_WAIT_S]
    assert len(models.calls) == 2


def test_gemini_retries_once_when_busy() -> None:
    provider, models, waits = gemini([gemini_error(503), "OK"])
    assert provider.complete_text("sys", "hi") == "OK"
    assert waits == [config.LLM_RATE_LIMIT_WAIT_S] and len(models.calls) == 2


def test_gemini_gives_up_after_second_429() -> None:
    provider, models, _ = gemini([gemini_error(429), gemini_error(429)])
    with pytest.raises(LLMRateLimited):
        provider.complete_text("sys", "hi")
    assert len(models.calls) == 2


@pytest.mark.parametrize(("outcome", "error"), [
    (gemini_error(504), LLMTimeout),
    (httpx.ReadTimeout("slow"), LLMTimeout),
    (gemini_error(500), LLMUnavailable),
    (gemini_error(400), LLMUnavailable),
    (httpx.ConnectError("offline"), LLMUnavailable),
])
def test_gemini_errors_are_typed(outcome: Exception, error: type[Exception]) -> None:
    provider, _, _ = gemini([outcome])
    with pytest.raises(error):
        provider.complete_text("sys", "hi")


def test_gemini_bad_json_and_wrong_schema_raise_bad_response() -> None:
    provider, _, _ = gemini(["not json", '{"other": 1}', ""])
    for _ in range(3):
        with pytest.raises(LLMBadResponse):
            provider.complete_json("sys", "hi", Reply)


# ---------------------------------------------------------------- NVIDIA
def test_nvidia_uses_only_final_content() -> None:
    provider, completions, _ = nvidia(['{"ok": false}'])
    assert provider.complete_json("sys", "hi", Reply) == {"ok": False}
    call = completions.calls[0]
    assert call["model"] == "nemotron-test"
    assert call["temperature"] == config.LLM_TEMPERATURE
    assert call["timeout"] == config.LLM_TIMEOUT_S
    assert [m["role"] for m in call["messages"]] == ["system", "user"]
    assert call["extra_body"] == config.NVIDIA_EXTRA_BODY


def test_nvidia_retries_empty_content_once_with_larger_budget() -> None:
    provider, completions, _ = nvidia([None, "Final answer"])
    assert provider.complete_text("sys", "hi") == "Final answer"
    assert [c["max_tokens"] for c in completions.calls] == [config.LLM_MAX_TOKENS, config.LLM_EMPTY_RETRY_MAX_TOKENS]


def test_nvidia_empty_twice_is_bad_response() -> None:
    provider, completions, _ = nvidia(["", ""])
    with pytest.raises(LLMBadResponse):
        provider.complete_text("sys", "hi")
    assert len(completions.calls) == 2


def test_nvidia_retries_once_on_429() -> None:
    provider, completions, waits = nvidia([nvidia_rate_limit(), "OK"])
    assert provider.complete_text("sys", "hi") == "OK"
    assert waits == [config.LLM_RATE_LIMIT_WAIT_S]
    assert len(completions.calls) == 2


def test_nvidia_busy_twice_raises_rate_limited() -> None:
    busy = openai.InternalServerError("busy", response=httpx.Response(503, request=NVIDIA_REQUEST), body=None)
    provider, completions, _ = nvidia([busy, busy])
    with pytest.raises(LLMRateLimited):
        provider.complete_text("sys", "hi")
    assert len(completions.calls) == 2


@pytest.mark.parametrize(("outcome", "error"), [
    (openai.APITimeoutError(request=NVIDIA_REQUEST), LLMTimeout),
    (openai.APIConnectionError(request=NVIDIA_REQUEST), LLMUnavailable),
    (openai.AuthenticationError("bad key", response=httpx.Response(401, request=NVIDIA_REQUEST), body=None),
     LLMUnavailable),
])
def test_nvidia_errors_are_typed(outcome: Exception, error: type[Exception]) -> None:
    provider, _, _ = nvidia([outcome])
    with pytest.raises(error):
        provider.complete_text("sys", "hi")


# ---------------------------------------------------------------- none and auto selection
def test_none_provider_raises_not_configured() -> None:
    with pytest.raises(LLMNotConfigured):
        NoneProvider().complete_text("sys", "hi")
    with pytest.raises(LLMNotConfigured):
        NoneProvider().complete_json("sys", "hi", Reply)


class ProbeProvider(Provider):
    def __init__(self, name: str, works: bool) -> None:
        super().__init__(f"{name}-model")
        self.name = name  # type: ignore[assignment]
        self.works = works
        self.probed = False

    def _call(self, system: str, user: str, json_mode: bool, timeout_s: float) -> str:
        self.probed = True
        if not self.works:
            raise LLMUnavailable("down")
        return "OK"


def settings(provider: str, gemini_key: str = "g", nvidia_key: str = "n") -> Settings:
    return Settings(_env_file=None, llm_provider=provider, gemini_api_key=gemini_key, gemini_model="gm",  # type: ignore[call-arg]
                    nvidia_api_key=nvidia_key, nvidia_model="nm")


def factories(gemini_works: bool, nvidia_works: bool) -> tuple[dict[str, Any], dict[str, ProbeProvider]]:
    built: dict[str, ProbeProvider] = {}

    def make(name: str, works: bool) -> Any:
        def factory(_: Settings) -> ProbeProvider:
            built[name] = ProbeProvider(name, works)
            return built[name]
        return factory
    return {"gemini": make("gemini", gemini_works), "nvidia": make("nvidia", nvidia_works)}, built


def test_auto_prefers_gemini_when_it_works() -> None:
    made, built = factories(True, True)
    provider, status = select_provider(settings("auto"), made)
    assert (provider.name, status.provider, status.model) == ("gemini", "gemini", "gemini-model")
    assert "nvidia" not in built


def test_auto_falls_back_to_nvidia_when_gemini_fails() -> None:
    made, built = factories(False, True)
    provider, status = select_provider(settings("auto"), made)
    assert provider.name == "nvidia" and built["gemini"].probed
    assert status.notes == ["gemini: test failed (LLMUnavailable)"]


def test_auto_falls_back_to_none_when_both_fail() -> None:
    made, _ = factories(False, False)
    provider, status = select_provider(settings("auto"), made)
    assert provider.name == "none" and status.model is None
    assert len(status.notes) == 2


def test_auto_skips_providers_without_a_key() -> None:
    made, built = factories(True, True)
    provider, status = select_provider(settings("auto", gemini_key=""), made)
    assert provider.name == "nvidia" and "gemini" not in built
    assert status.notes == ["gemini: key or model missing"]


def test_explicit_provider_is_used_without_a_probe() -> None:
    made, built = factories(False, True)
    provider, _ = select_provider(settings("gemini"), made)
    assert provider.name == "gemini" and not built["gemini"].probed


def test_explicit_none_and_missing_key() -> None:
    made, _ = factories(True, True)
    assert select_provider(settings("none"), made)[0].name == "none"
    provider, status = select_provider(settings("nvidia", nvidia_key=""), made)
    assert provider.name == "none" and status.notes == ["nvidia: key or model missing"]
