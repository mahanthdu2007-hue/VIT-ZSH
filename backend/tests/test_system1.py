"""§7.3 System 1: abstain rule, KeywordBackend, the JevBackend stub and the backend factory (offline, fast)."""

from pathlib import Path

import pytest

from app.engine import config
from app.engine.loader import get_dataset
from app.engine.system1 import (
    JevBackend,
    KeywordBackend,
    NotConfigured,
    build_backend,
    build_decision,
    get_decision_model,
    run_decisions,
)
from app.models.schemas import DemoProfile
from tests.factories import parent, school_student

DOMAIN = config.DECISION_STUDENT_DOMAIN
CONCERNS = config.DECISION_PARENT_CONCERNS


def persona(persona_id: str) -> DemoProfile:
    return next(p for p in get_dataset().demo_profiles if p.id == persona_id)


@pytest.mark.parametrize(("top", "second", "abstained"), [
    (0.9, 0.2, False),
    (0.45, 0.2, False),   # confidence exactly at the threshold is kept
    (0.44, 0.1, True),    # confidence < 0.45
    (0.9, 0.76, True),    # margin 0.14 < 0.15
    (0.9, 0.75, False),   # margin 0.15 is kept
])
def test_abstain_rule(top: float, second: float, abstained: bool) -> None:
    decision = build_decision("q", {"a": second, "b": top, "c": 0.0}, "test")
    assert decision.confidence == top
    assert decision.margin == pytest.approx(top - second)
    assert decision.abstained is abstained
    assert decision.choice == (None if abstained else "b")


def test_single_option_margin_is_its_confidence() -> None:
    decision = build_decision("q", {"a": 0.6}, "test")
    assert decision.margin == 0.6 and decision.choice == "a"


@pytest.mark.parametrize(("persona_id", "domain"), [
    ("ananya", "Technology"),
    ("rahul", "Finance & Maths"),
    ("meera", "Arts & Design"),
])
def test_keyword_backend_picks_persona_domain(persona_id: str, domain: str) -> None:
    profile = persona(persona_id)
    decisions = run_decisions(KeywordBackend(), profile.student, profile.parent)
    by_id = {d.question_id: d for d in decisions}
    assert set(by_id) == {DOMAIN, CONCERNS}
    assert set(by_id[DOMAIN].probabilities) == set(config.DOMAINS)
    assert set(by_id[CONCERNS].probabilities) == set(config.PARENT_CONCERNS)
    assert by_id[DOMAIN].choice == domain
    assert all(d.backend == "keyword" for d in decisions)


def test_keyword_confidence_is_capped() -> None:
    text = "python python python coding software computers ai"
    decision = KeywordBackend().decide(text, DOMAIN, list(config.DOMAINS), "{}")
    assert decision.confidence == config.KEYWORD_CONFIDENCE_CAP
    assert all(0.0 <= p <= config.KEYWORD_CONFIDENCE_CAP for p in decision.probabilities.values())


def test_keyword_matches_whole_words_only() -> None:
    decision = KeywordBackend().decide("We need financial aid and a detailed plan.", DOMAIN,
                                       list(config.DOMAINS), "{}")
    assert decision.probabilities["Technology"] == 0.0  # "aid" and "detailed" do not count as "ai"


def test_keyword_tie_abstains() -> None:
    decision = KeywordBackend().decide("I like software and medicine.", DOMAIN, list(config.DOMAINS), "{}")
    assert decision.abstained and decision.choice is None


def test_no_keywords_abstains_with_zero_probabilities() -> None:
    decision = KeywordBackend().decide("I like long walks.", DOMAIN, list(config.DOMAINS), "{}")
    assert decision.abstained and decision.confidence == 0.0


class ExplodingModel:
    name = "exploding"

    def decide(self, state: str, question_id: str, options: list[str],
               hypothesis_template: str) -> None:
        raise AssertionError("the model must not be called for empty text")


def test_empty_text_abstains_without_calling_the_model() -> None:
    decisions = run_decisions(ExplodingModel(), school_student(), parent(700000, 500000))  # type: ignore[arg-type]
    assert [d.question_id for d in decisions] == [DOMAIN, CONCERNS]
    assert all(d.abstained and d.confidence == 0.0 and d.backend == "exploding" for d in decisions)


def test_jev_stub_raises_not_configured() -> None:
    with pytest.raises(NotConfigured):
        JevBackend()


def test_factory_keyword() -> None:
    backend, failures = build_backend("keyword", ())
    assert isinstance(backend, KeywordBackend) and failures == []


def test_factory_jev_falls_back_to_keyword() -> None:
    backend, failures = build_backend("jev", ())
    assert isinstance(backend, KeywordBackend)
    assert len(failures) == 1 and failures[0].startswith("jev")


def test_factory_falls_back_through_every_model_to_keyword(tmp_path: Path) -> None:
    missing = (str(tmp_path / "no_model_here"), str(tmp_path / "nor_here"))
    backend, failures = build_backend("nli", missing)
    assert isinstance(backend, KeywordBackend)
    assert len(failures) == 2


def test_process_backend_follows_settings() -> None:
    assert get_decision_model().name == "keyword"  # tests/conftest.py sets SYSTEM1_BACKEND=keyword
