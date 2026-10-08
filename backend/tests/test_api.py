"""§13 API: every endpoint, saved assessments, the DEMO_MODE cache, What-If latency and determinism."""

import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import demo_cache, services, storage
from app.engine import config
from app.engine.loader import get_dataset
from app.main import app
from app.settings import get_settings

DATA = get_dataset()
LATENCY_RUNS = 10


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    with TestClient(app) as started:
        yield started


def profile_body(profile_id: str) -> dict[str, Any]:
    profile = next(p for p in DATA.demo_profiles if p.id == profile_id)
    return {"student": profile.student.model_dump(mode="json"), "parent": profile.parent.model_dump(mode="json")}


@pytest.fixture(scope="module")
def ananya(client: TestClient) -> dict[str, Any]:
    response = client.post("/api/assess", json=profile_body("ananya"))
    assert response.status_code == 200
    return response.json()


def test_health_reports_dataset_counts(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body["dataset"] == {"careers": len(DATA.careers), "scholarships": len(DATA.scholarships),
                               "exams": len(DATA.exams), "cities": len(DATA.cities), "demo_profiles": 3}


@pytest.mark.parametrize("track", ["school", "college"])
def test_questions_hide_answer_keys(client: TestClient, track: str) -> None:
    body = client.get(f"/api/questions/{track}").json()
    assert body["track"] == track
    assert len(body["aptitude"]) == config.APTITUDE_ITEMS_TOTAL
    assert all("answer" not in item for item in body["aptitude"])
    assert (body["skills"] is not None) == (track == "college")


def test_questions_unknown_track(client: TestClient) -> None:
    assert client.get("/api/questions/university").status_code == 422


def test_demo_profiles(client: TestClient) -> None:
    body = client.get("/api/demo-profiles").json()
    assert [p["id"] for p in body] == ["ananya", "rahul", "meera"]


def test_careers_list_and_detail(client: TestClient) -> None:
    listed = client.get("/api/careers").json()
    assert len(listed) == len(DATA.careers)
    assert set(listed[0]) == {"id", "name", "domain", "steam", "summary"}
    detail = client.get("/api/careers/ai_ml_engineer").json()
    assert detail["name"] == "AI/ML Engineer" and detail["pathways"] and detail["data_note"]
    assert client.get("/api/careers/astronaut").status_code == 404


def test_assess_returns_a_full_result(ananya: dict[str, Any]) -> None:
    assert ananya["id"]
    assert len(ananya["ranking"]) == config.TOP_CAREERS_LIMIT
    assert ananya["ranking"][0]["career_id"] in ananya["details"]
    assert ananya["explanations"]["source"] == "template"
    assert len(ananya["explanations"]["items"]) >= config.EXPLAIN_TOP_N
    assert set(ananya["trace"]) == {"ingest", "vectorize", "system1", "solver", "matcher", "conflict", "market",
                                    "scoring", "ranking"}
    assert ananya["trace"]["system1"]["backend"] == "keyword"
    assert 0 <= ananya["conflict"]["index"] <= 100
    assert ananya["confidence"]["band"] in {"High", "Medium", "Low"}


def test_assess_rejects_invalid_input(client: TestClient) -> None:
    body = profile_body("ananya")
    body["parent"]["education_budget_inr"] = -5
    assert client.post("/api/assess", json=body).status_code == 422


def test_assessment_is_saved_with_its_decisions(ananya: dict[str, Any]) -> None:
    inputs = storage.load_inputs(ananya["id"])
    assert inputs is not None
    assert [d.model_dump(mode="json") for d in inputs.decisions] == ananya["trace"]["system1"]["decisions"]
    assert inputs.as_of.isoformat() == ananya["as_of"]
    saved = storage.load_result(ananya["id"])
    assert saved is not None and saved.model_dump(mode="json") == ananya


def test_explanations_endpoint(client: TestClient, ananya: dict[str, Any]) -> None:
    response = client.get(f"/api/explanations/{ananya['id']}")
    assert response.status_code == 200
    assert response.json() == ananya["explanations"]
    assert client.get("/api/explanations/no-such-id").status_code == 404


def test_whatif_by_assessment_id(client: TestClient, ananya: dict[str, Any]) -> None:
    response = client.post("/api/whatif", json={"assessment_id": ananya["id"], "overrides": {"budget": 300000}})
    assert response.status_code == 200
    body = response.json()
    assert body["assessment_id"] == ananya["id"]
    assert body["overrides"]["budget"] == 300000
    assert any(c["reason"] and "Financial Fit" in c["reason"] for c in body["changes"])


def test_whatif_without_overrides_matches_the_assessment(client: TestClient, ananya: dict[str, Any]) -> None:
    body = client.post("/api/whatif", json={"assessment_id": ananya["id"]}).json()
    assert [r["career_id"] for r in body["ranking"]] == [r["career_id"] for r in ananya["ranking"]]
    assert all(c["score_delta"] == 0 and c["reason"] is None for c in body["changes"])


def test_whatif_by_full_profile(client: TestClient) -> None:
    body = {"profile": profile_body("rahul"), "overrides": {"top_priority": "salary"}}
    response = client.post("/api/whatif", json=body)
    assert response.status_code == 200
    assert response.json()["assessment_id"] is None


def test_whatif_errors(client: TestClient, ananya: dict[str, Any]) -> None:
    assert client.post("/api/whatif", json={"assessment_id": "no-such-id"}).status_code == 404
    both = {"assessment_id": ananya["id"], "profile": profile_body("ananya")}
    assert client.post("/api/whatif", json=both).status_code == 422
    assert client.post("/api/whatif", json={}).status_code == 422
    bad = {"assessment_id": ananya["id"], "overrides": {"budget": 300000, "income": 1}}
    assert client.post("/api/whatif", json=bad).status_code == 422


def test_whatif_latency_after_warm_up(client: TestClient, ananya: dict[str, Any]) -> None:
    """§11 target: < 300 ms for the whole request, including loading the saved assessment."""
    body = {"assessment_id": ananya["id"], "overrides": {"budget": 300000}}
    client.post("/api/whatif", json=body)  # warm-up
    times = []
    for _ in range(LATENCY_RUNS):
        start = time.perf_counter()
        assert client.post("/api/whatif", json=body).status_code == 200
        times.append((time.perf_counter() - start) * 1000)
    assert max(times) < config.WHATIF_TARGET_MS, times


def test_assess_is_deterministic_apart_from_the_id(client: TestClient) -> None:
    first = client.post("/api/assess", json=profile_body("meera")).json()
    second = client.post("/api/assess", json=profile_body("meera")).json()
    assert first.pop("id") != second.pop("id")
    assert first == second


def test_demo_mode_caches_demo_profiles(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(demo_cache, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(services, "get_settings", lambda: get_settings().model_copy(update={"demo_mode": True}))
    first = client.post("/api/assess", json=profile_body("rahul")).json()
    assert len(list(tmp_path.glob("demo_rahul_*.json"))) == 1

    def fail(*args: object, **kwargs: object) -> None:
        raise AssertionError("the pipeline must not run on a cache hit")

    monkeypatch.setattr(services, "run_pipeline", fail)
    second = client.post("/api/assess", json=profile_body("rahul")).json()
    assert first.pop("id") != second.pop("id")
    assert first == second
    assert storage.load_inputs(client.post("/api/assess", json=profile_body("rahul")).json()["id"]) is not None


def test_demo_mode_does_not_cache_other_profiles(client: TestClient, tmp_path: Path,
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(demo_cache, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(services, "get_settings", lambda: get_settings().model_copy(update={"demo_mode": True}))
    body = profile_body("rahul")
    body["parent"]["education_budget_inr"] = 160000
    assert client.post("/api/assess", json=body).status_code == 200
    assert not list(tmp_path.iterdir())
