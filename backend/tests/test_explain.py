"""§12 System 2 explanations with a mocked LLM: guardrail, JSON failures, the none path and the lazy API."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from strategies import AS_OF, DATA, stand_in_decisions

from app import services
from app.engine import config
from app.engine.pipeline import run_pipeline
from app.main import app
from app.models.schemas import Explanations, PipelineResult
from app.rag import guardrail, index
from app.rag.explain import llm_explanations
from app.rag.llm import NoneProvider, Provider
from app.rag.templates import explained_ids, template_explanations

CITY_NAMES = {c.id: c.name for c in DATA.cities}
ANANYA = next(p for p in DATA.demo_profiles if p.id == "ananya")


@pytest.fixture(autouse=True)
def no_chroma(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unit tests read documents from the dataset; the real Chroma index is tested in the slow test below."""
    monkeypatch.setattr(index, "_collection", lambda: None)


@pytest.fixture(scope="module")
def ananya() -> tuple[PipelineResult, Explanations]:
    decisions = stand_in_decisions(dict.fromkeys(config.DOMAINS, 0.3), {})
    result = run_pipeline(ANANYA.student, ANANYA.parent, DATA, AS_OF, decisions=decisions)
    return result, template_explanations(result, CITY_NAMES, ANANYA.student.home_city,
                                         ANANYA.parent.annual_income_inr)


Item = Callable[[dict[str, Any]], dict[str, Any] | None]


def good_item(engine: dict[str, Any]) -> dict[str, Any]:
    """A well-behaved LLM: numbers copied from ENGINE_RESULT, some written in other Indian formats."""
    cost = engine["cost_indicative"]["cost_after_scholarship"]
    lakh = int(cost.replace("₹", "").replace(",", "")) / 100000
    return {
        "career_id": engine["career_id"],
        "why": [f"{engine['career']} matches how you think.",
                f"Your Student Fit is {engine['points']['Student Fit']['earned']} out of 30.",
                f"The route costs about ₹{lakh:g} lakh after scholarships, an indicative estimate."],
        "why_not": [f"The Economic Disruption Index is {engine['economic_disruption_index']}.",
                    "Jobs may need you to move cities."],
        "roadmap_narrative": f"Start with {engine['suggested_route']['steps'][0]}. It costs around {cost}.",
        "cited_ids": [f"career:{engine['career_id']}", "not_a_real_id"],
    }


def engines_of(user: str) -> list[dict[str, Any]]:
    return json.loads(user.split("ENGINE_RESULT:\n", 1)[1].split("\n\nCONTEXT:", 1)[0])


class ScriptedProvider(Provider):
    """Answers the one explanation request with {"items": [item(engine) for each career]}, or with raw text."""
    name = "gemini"  # type: ignore[assignment]

    def __init__(self, item: Item = good_item, raw: str | None = None) -> None:
        super().__init__("test-model")
        self.item, self.raw = item, raw
        self.prompts: list[tuple[str, str]] = []

    def _call(self, system: str, user: str, json_mode: bool, timeout_s: float) -> str:
        self.prompts.append((system, user))
        if self.raw is not None:
            return self.raw
        items = [self.item(engine) for engine in engines_of(user)]
        return json.dumps({"items": [i for i in items if i is not None]})


def run(result: PipelineResult, templates: Explanations, provider: Provider) -> Explanations:
    return llm_explanations(provider, result, templates, CITY_NAMES, ANANYA.student, ANANYA.parent)


# ---------------------------------------------------------------- guardrail unit tests
@pytest.mark.parametrize("written", ["₹5,00,000", "500000", "5 lakh", "5L", "₹5L", "Rs. 5 lakhs", "₹5.0 lakh",
                                     "5,00,000 rupees", "₹ 500000"])
def test_reformatted_indian_amounts_are_supported(written: str) -> None:
    allowed = guardrail.allowed_values({"budget": 500000})
    assert guardrail.unsupported_numbers(f"The budget is {written}.", allowed) == []


@pytest.mark.parametrize("written", ["₹6,00,000", "600000", "6 lakh", "6L", "₹50,000", "50 lakh", "₹5 crore"])
def test_amounts_not_in_the_sources_are_flagged(written: str) -> None:
    allowed = guardrail.allowed_values({"budget": 500000})
    assert guardrail.unsupported_numbers(f"The budget is {written}.", allowed) != []


def test_lpa_ranges_percentages_and_rounding() -> None:
    allowed = guardrail.allowed_values({"salary": "entry 6–12 LPA", "fit": 0.85, "points": 26.43}, ["takes 4 years"])
    for ok in ["6 to 12 LPA", "₹12 lakh a year", "₹6,00,000", "85%", "26.4 points", "26 points", "4 years"]:
        assert guardrail.unsupported_numbers(ok, allowed) == [], ok
    for bad in ["7 LPA", "90%", "26.5 points", "5 years", "₹2–5 lakh"]:
        assert guardrail.unsupported_numbers(bad, allowed) != [], bad


def test_numbers_inside_words_are_not_numbers() -> None:
    assert guardrail.extract_numbers("deberta-v3 and B2B work") == []


# ---------------------------------------------------------------- explanations with a mocked LLM
def test_guardrail_present_keeps_llm_text(ananya: tuple[PipelineResult, Explanations]) -> None:
    result, templates = ananya
    provider = ScriptedProvider()
    explained = run(result, templates, provider)
    assert len(provider.prompts) == 1  # one request for every career (free-tier request limits)
    assert explained.source == "llm" and explained.status == "ready"
    assert [i.career_id for i in explained.items] == explained_ids(result)
    assert explained.trace is not None and explained.trace.guardrail_hits == []
    assert explained.trace.provider == "gemini" and explained.trace.retrieval == "dataset"
    for item in explained.items:
        assert item.source == "llm"
        assert len(item.why) == config.EXPLAIN_WHY_COUNT and len(item.why_not) == config.EXPLAIN_WHY_NOT_COUNT
        assert "lakh" in item.why[2]
        assert [c.id for c in item.citations] == [item.career_id]  # the unknown id was dropped
        assert item.citations[0].text.startswith(result.details[item.career_id].career.name)
    system, user = provider.prompts[0]
    assert "Use only facts in CONTEXT and ENGINE_RESULT" in system and "JSON schema" in system
    assert "CONTEXT:\n[career:" in user
    assert [e["career_id"] for e in engines_of(user)] == explained_ids(result)


def test_guardrail_missing_number_replaces_sentence(ananya: tuple[PipelineResult, Explanations]) -> None:
    result, templates = ananya

    def item(engine: dict[str, Any]) -> dict[str, Any]:
        data = good_item(engine)
        data["why"][1] = "You will earn ₹99,99,999 in your first year."
        data["roadmap_narrative"] += " Most students finish in 7.5 years."
        return data

    explained = run(result, templates, ScriptedProvider(item))
    template_by_id = {t.career_id: t for t in templates.items}
    assert explained.trace is not None
    for item in explained.items:
        assert item.why[1] == template_by_id[item.career_id].why[1]
        assert "7.5" not in item.roadmap_narrative and item.roadmap_narrative.startswith("Start with")
    hits = explained.trace.guardrail_hits
    assert len(hits) == 2 * len(explained.items)
    why_hit = next(h for h in hits if h.field == "why[1]")
    assert why_hit.unsupported == ["₹99,99,999"] and why_hit.action == "replaced"
    assert next(h for h in hits if h.field == "roadmap_narrative").action == "removed"


def test_narrative_with_only_bad_sentences_uses_template(ananya: tuple[PipelineResult, Explanations]) -> None:
    result, templates = ananya

    def item(engine: dict[str, Any]) -> dict[str, Any]:
        return good_item(engine) | {"roadmap_narrative": "It takes 977 years and costs ₹9 crore."}

    explained = run(result, templates, ScriptedProvider(item))
    for item, template in zip(explained.items, templates.items, strict=True):
        assert item.roadmap_narrative == template.roadmap_narrative


def test_short_lists_are_filled_from_templates(ananya: tuple[PipelineResult, Explanations]) -> None:
    result, templates = ananya

    def short(engine: dict[str, Any]) -> dict[str, Any]:
        data = good_item(engine)
        return data | {"why": data["why"][:1], "why_not": []}

    item, template = run(result, templates, ScriptedProvider(short)).items[0], templates.items[0]
    assert item.why[1:] == template.why[1:] and item.why_not == template.why_not


@pytest.mark.parametrize("raw", ["Sorry, I can't help with that.", '{"career_id": "x"}', "```json\n{broken\n```", "",
                                 '{"items": []}', '{"items": [{"career_id": "ai_ml_engineer"}]}'])
def test_json_failure_falls_back_to_template(ananya: tuple[PipelineResult, Explanations], raw: str) -> None:
    result, templates = ananya
    explained = run(result, templates, ScriptedProvider(raw=raw))
    assert explained.source == "template"
    assert [i.model_dump() for i in explained.items] == [t.model_dump() for t in templates.items]
    assert explained.trace is not None
    assert all(c.fallback_reason and c.fallback_reason.startswith("LLMBadResponse") for c in explained.trace.careers)


def test_one_failing_career_does_not_affect_the_others(ananya: tuple[PipelineResult, Explanations]) -> None:
    result, templates = ananya
    first = explained_ids(result)[0]
    explained = run(result, templates, ScriptedProvider(
        lambda e: {"career_id": first, "why": "not a list"} if e["career_id"] == first else good_item(e)))
    assert explained.source == "llm"
    assert [i.source for i in explained.items] == ["template"] + ["llm"] * (len(explained.items) - 1)


def test_none_path_uses_templates(ananya: tuple[PipelineResult, Explanations]) -> None:
    result, templates = ananya
    explained = run(result, templates, NoneProvider())
    assert explained.source == "template" and explained.status == "ready"
    assert [i.model_dump() for i in explained.items] == [t.model_dump() for t in templates.items]
    assert explained.trace is not None and explained.trace.provider == "none"
    assert all(c.fallback_reason and c.fallback_reason.startswith("LLMNotConfigured")
               for c in explained.trace.careers)


def test_retrieval_is_filtered_to_explained_careers(ananya: tuple[PipelineResult, Explanations]) -> None:
    result, templates = ananya
    explained = run(result, templates, ScriptedProvider())
    assert explained.trace is not None
    for career_trace in explained.trace.careers:
        for doc_id in career_trace.retrieved_ids:
            kind, rest = doc_id.split(":", 1)
            if kind in ("career", "pathway"):
                assert rest.split(":")[0] == career_trace.career_id


@pytest.mark.parametrize("profile_id", ["ananya", "rahul", "meera"])
def test_template_sentences_pass_the_guardrail(profile_id: str) -> None:
    """The fallback text must itself pass the check: ENGINE_RESULT carries every value the templates quote."""
    profile = next(p for p in DATA.demo_profiles if p.id == profile_id)
    result = run_pipeline(profile.student, profile.parent, DATA, AS_OF,
                          decisions=stand_in_decisions(dict.fromkeys(config.DOMAINS, 0.3), {}))
    templates = template_explanations(result, CITY_NAMES, profile.student.home_city, profile.parent.annual_income_inr)
    provider = ScriptedProvider()
    explained = llm_explanations(provider, result, templates, CITY_NAMES, profile.student, profile.parent)
    assert explained.trace is not None
    engines = {e["career_id"]: e for e in engines_of(provider.prompts[0][1])}
    docs = index.dataset_documents()
    for template, career_trace in zip(templates.items, explained.trace.careers, strict=True):
        own_text = [docs[d].text for d in career_trace.retrieved_ids]
        allowed = guardrail.allowed_values(engines[template.career_id], own_text)
        for sentence in [*template.why, *template.why_not, *guardrail.split_sentences(template.roadmap_narrative)]:
            assert guardrail.unsupported_numbers(sentence, allowed) == [], sentence


# ---------------------------------------------------------------- lazy API
def test_api_none_mode_is_ready_immediately() -> None:
    client = TestClient(app)
    profile = ANANYA.model_dump(mode="json")
    body = client.post("/api/assess", json={"student": profile["student"], "parent": profile["parent"]}).json()
    assert body["explanations"]["status"] == "ready" and body["explanations"]["source"] == "template"
    later = client.get(f"/api/explanations/{body['id']}").json()
    assert later == body["explanations"]


def test_api_writes_llm_explanations_in_the_background(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(services, "get_llm", lambda: ScriptedProvider())
    client = TestClient(app)
    profile = ANANYA.model_dump(mode="json")
    body = client.post("/api/assess", json={"student": profile["student"], "parent": profile["parent"]}).json()
    assert body["explanations"]["status"] == "pending" and body["explanations"]["source"] == "template"
    later = client.get(f"/api/explanations/{body['id']}").json()  # TestClient ran the background task
    assert later["status"] == "ready" and later["source"] == "llm"
    assert later["trace"]["guardrail_hits"] == []
    assert client.get("/api/explanations/does-not-exist").status_code == 404


# ---------------------------------------------------------------- real Chroma index
@pytest.mark.slow
def test_chroma_index_filtered_retrieval(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    count = index.rebuild(DATA, tmp_path)
    assert count == len(index.build_documents(DATA))
    import chromadb
    collection = chromadb.PersistentClient(path=str(tmp_path)).get_collection(index.COLLECTION)
    monkeypatch.setattr(index, "_collection", lambda: collection)
    docs, source = index.retrieve(["ai_ml_engineer", "data_scientist"], ["exam:jee_main"])
    assert source == "chroma"
    assert {d.career_id for d in docs} == {"ai_ml_engineer", "data_scientist", ""}
    assert [d.doc_id for d in docs if d.career_id == ""] == ["exam:jee_main"]
