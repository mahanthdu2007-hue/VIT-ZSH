"""§7.3 System 1 Decision Layer: classifies free text into typed, auditable decisions.

System 1 only classifies text. It never produces scores, costs or rankings (§2.1).
Backends share one protocol, so the pipeline does not care which one is active:
ZeroShotNLIBackend (default), KeywordBackend (offline fallback) and JevBackend (stub).
"""

import re
import threading
from collections.abc import Callable
from functools import lru_cache
from typing import Any, Protocol

from app.engine import config
from app.models.schemas import ParentInput, StudentInput, TypedDecision

KEYWORD_BACKEND_NAME = "keyword"
JEV_BACKEND_NAME = "jev"


class NotConfigured(Exception):
    """A backend that needs credentials or a licence that this install does not have."""


class DecisionModel(Protocol):
    name: str

    def decide(self, state: str, question_id: str, options: list[str],
               hypothesis_template: str) -> TypedDecision: ...


def build_decision(question_id: str, probabilities: dict[str, float], backend: str) -> TypedDecision:
    """Apply the §7.3 abstain rule to per-label probabilities."""
    ranked = sorted(probabilities.values(), reverse=True)
    confidence = ranked[0] if ranked else 0.0
    margin = confidence - (ranked[1] if len(ranked) > 1 else 0.0)
    abstained = confidence < config.ABSTAIN_MIN_CONFIDENCE or margin < config.ABSTAIN_MIN_MARGIN
    choice = None if abstained else max(probabilities, key=lambda label: probabilities[label])
    return TypedDecision(
        question_id=question_id,
        choice=choice,
        probabilities=probabilities,
        confidence=confidence,
        margin=margin,
        abstained=abstained,
        backend=backend,
    )


def label_phrase(question_id: str, option: str) -> str:
    return config.LABEL_PHRASES.get(question_id, {}).get(option, option)


class ZeroShotNLIBackend:
    """HuggingFace zero-shot classification (NLI), multi-label. The model loads once, on first use."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.name = f"zero_shot_nli:{model_name}"
        self._classifier: Callable[..., Any] | None = None
        self._lock = threading.Lock()

    def load(self) -> None:
        with self._lock:
            if self._classifier is None:
                from transformers import pipeline  # heavy import, only when the model is used

                self._classifier = pipeline("zero-shot-classification", model=self.model_name,
                                            device=-1, dtype=config.SYSTEM1_DTYPE)

    def decide(self, state: str, question_id: str, options: list[str],
               hypothesis_template: str) -> TypedDecision:
        self.load()
        assert self._classifier is not None
        phrases = {label_phrase(question_id, option): option for option in options}
        output = self._classifier(state, candidate_labels=list(phrases),
                                  hypothesis_template=hypothesis_template, multi_label=True)
        scores = dict(zip(output["labels"], output["scores"], strict=True))
        probabilities = {phrases[phrase]: float(score) for phrase, score in scores.items()}
        return build_decision(question_id, {option: probabilities[option] for option in options}, self.name)


def keyword_hits(text: str, keywords: tuple[str, ...]) -> int:
    lowered = text.lower()
    return sum(len(re.findall(rf"\b{re.escape(keyword)}\b", lowered)) for keyword in keywords)


class KeywordBackend:
    """Offline fallback: counts whole-word keyword hits per label (config.KEYWORDS).

    Each label's probability is its share of the top label's hits, scaled to the 0.5 cap, so this
    backend is never more than 0.5 confident and abstains whenever two labels are close.
    """

    name = KEYWORD_BACKEND_NAME

    def decide(self, state: str, question_id: str, options: list[str],
               hypothesis_template: str) -> TypedDecision:
        keywords = config.KEYWORDS.get(question_id, {})
        hits = {option: keyword_hits(state, keywords.get(option, ())) for option in options}
        most = max(hits.values(), default=0)
        probabilities = {
            option: config.KEYWORD_CONFIDENCE_CAP * count / most if most else 0.0
            for option, count in hits.items()
        }
        return build_decision(question_id, probabilities, self.name)


class JevBackend:
    """Stub for a commercial System One decision model (drop-in upgrade path).

    To upgrade: implement `decide` so it sends `state`, `options` and `hypothesis_template` to the
    vendor model and returns a TypedDecision via `build_decision(question_id, probabilities, self.name)`,
    with one probability per option in [0, 1]. Nothing else changes: the pipeline, the abstain rule,
    confidence (§7.8) and the trace already work with any DecisionModel. Then set SYSTEM1_BACKEND=jev.
    Until configured, the factory catches NotConfigured and falls back to KeywordBackend.
    """

    name = JEV_BACKEND_NAME

    def __init__(self) -> None:
        raise NotConfigured("JevBackend has no vendor credentials configured")

    def decide(self, state: str, question_id: str, options: list[str],
               hypothesis_template: str) -> TypedDecision:
        raise NotConfigured("JevBackend has no vendor credentials configured")


def build_backend(kind: str, model_names: tuple[str, ...]) -> tuple[DecisionModel, list[str]]:
    """Pick the configured backend; on any load failure fall through to the next, ending at keywords.

    Returns the backend and the reasons for every fallback taken (empty when the first choice worked).
    """
    failures: list[str] = []
    if kind == JEV_BACKEND_NAME:
        try:
            return JevBackend(), failures
        except NotConfigured as exc:
            failures.append(f"jev: {exc}")
    elif kind != KEYWORD_BACKEND_NAME:
        for model_name in model_names:
            backend = ZeroShotNLIBackend(model_name)
            try:
                backend.load()
                return backend, failures
            except Exception as exc:  # any load error (offline, missing files, out of memory) → next option
                failures.append(f"{model_name}: {type(exc).__name__}: {exc}")
    return KeywordBackend(), failures


@lru_cache
def get_decision_model() -> DecisionModel:
    """The process-wide System 1 backend, chosen once from settings (SYSTEM1_BACKEND, SYSTEM1_MODEL)."""
    from app.settings import get_settings

    settings = get_settings()
    backend, _ = build_backend(settings.system1_backend,
                               (settings.system1_model, config.SYSTEM1_FALLBACK_MODEL))
    return backend


def decision_inputs(student: StudentInput, parent: ParentInput) -> list[tuple[str, str, tuple[str, ...]]]:
    """(question_id, text, options) for each §7.3 decision."""
    student_text = " ".join(t.strip() for t in (student.free_text_1, student.free_text_2) if t.strip())
    return [
        (config.DECISION_STUDENT_DOMAIN, student_text, config.DOMAINS),
        (config.DECISION_PARENT_CONCERNS, parent.free_text.strip(), config.PARENT_CONCERNS),
    ]


def run_decisions(model: DecisionModel, student: StudentInput, parent: ParentInput) -> list[TypedDecision]:
    """Run every §7.3 decision. Empty text abstains without calling the model."""
    decisions: list[TypedDecision] = []
    for question_id, text, options in decision_inputs(student, parent):
        if not text:
            decisions.append(build_decision(question_id, dict.fromkeys(options, 0.0), model.name))
            continue
        decisions.append(model.decide(text, question_id, list(options),
                                      config.HYPOTHESIS_TEMPLATES[question_id]))
    return decisions
