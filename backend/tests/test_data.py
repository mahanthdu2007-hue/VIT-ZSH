import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, get_args

import pytest
from pydantic import ValidationError

from app.engine import config
from app.engine.loader import DATA_DIR, load_dataset
from app.models.schemas import Career, CityId, Domain, ParentInput, SchoolStudentInput

BACKEND_DIR = Path(__file__).resolve().parents[1]
VALIDATOR = BACKEND_DIR / "scripts" / "validate_data.py"


def run_validator(data_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--data-dir", str(data_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def sample_career(**overrides: Any) -> dict[str, Any]:
    pathway = {
        "id": "btech_govt",
        "label": "B.Tech at a government college",
        "entry": "after_class_12",
        "steps": ["Class 12 PCM", "B.Tech"],
        "duration_years": 4,
        "cost_inr": {"min": 200000, "max": 500000},
        "institution_type": "govt",
        "entrance_exams": ["jee_main"],
        "quality": 0.8,
    }
    career = {
        "id": "test_career",
        "name": "Test career",
        "domain": "Technology",
        "steam": ["T"],
        "summary": "A career used only in tests.",
        "requirement_vector": {d: 0.5 for d in config.STUDENT_DIMENSIONS},
        "skills": [{"name": "Python", "importance": 0.9, "level_required": 0.8}],
        "pathways": [pathway, {**pathway, "id": "online", "institution_type": "online"}],
        "salary_inr_lpa": {"entry": [6, 12], "mid": [15, 30], "senior": [30, 60]},
        "growth_index": 0.8,
        "job_velocity": 0.8,
        "disruption_index": 0.2,
        "stability": 0.6,
        "risk_level": 0.5,
        "prestige": 0.7,
        "higher_studies_typical": False,
        "city_demand": {c: 0.5 for c in config.CITIES},
        "adjacent_careers": [],
        "sources": ["Test source"],
        "data_note": "Test data.",
    }
    return {**career, **overrides}


def test_validator_passes_on_project_data() -> None:
    result = run_validator(DATA_DIR)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "0 error(s)" in result.stdout


def test_validator_catches_broken_data(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    shutil.copytree(DATA_DIR, data_dir)

    questions_path = data_dir / "questions_school.json"
    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    questions["aptitude"][0]["answer"] = 9
    questions_path.write_text(json.dumps(questions), encoding="utf-8")

    broken = sample_career(adjacent_careers=["no_such_career"])
    broken["pathways"][0]["entrance_exams"] = ["no_such_exam"]
    broken["skills"][0]["name"] = "No such skill"
    (data_dir / "careers").mkdir(exist_ok=True)
    (data_dir / "careers" / "technology.json").write_text(json.dumps([broken]), encoding="utf-8")

    result = run_validator(data_dir)
    assert result.returncode == 1
    for expected in ("answer index 9", "no_such_career", "no_such_exam", "No such skill",
                     "Technology has 1, minimum is 10"):
        assert expected in result.stdout


def test_validator_enforces_total_once_every_domain_has_careers(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    shutil.copytree(DATA_DIR, data_dir)
    shutil.rmtree(data_dir / "careers")
    (data_dir / "careers").mkdir()
    one_per_domain = [sample_career(id=f"career_{i}", domain=d) for i, d in enumerate(config.DOMAINS)]
    (data_dir / "careers" / "all.json").write_text(json.dumps(one_per_domain), encoding="utf-8")

    result = run_validator(data_dir)
    assert result.returncode == 1
    assert "careers: 7 total, expected 55–60" in result.stdout


def test_validator_catches_incomplete_demo_profile(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    shutil.copytree(DATA_DIR, data_dir)
    profiles_path = data_dir / "demo_profiles.json"
    profiles = json.loads(profiles_path.read_text(encoding="utf-8"))
    del profiles[0]["student"]["riasec_answers"]["ria_i_1"]
    profiles[0]["student"]["dream_career_id"] = "astronaut"
    profiles[0]["parent"]["free_text"] = "Too short."
    profiles_path.write_text(json.dumps(profiles), encoding="utf-8")

    result = run_validator(data_dir)
    assert result.returncode == 1
    for expected in ("riasec answers missing ['ria_i_1']", "unknown dream career 'astronaut'",
                     "parent.free_text has 2 words"):
        assert expected in result.stdout


def test_validator_catches_salary_that_falls(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    shutil.copytree(DATA_DIR, data_dir)
    path = data_dir / "careers" / "technology.json"
    careers = json.loads(path.read_text(encoding="utf-8"))
    careers[0]["salary_inr_lpa"]["mid"] = [5, 10]
    path.write_text(json.dumps(careers), encoding="utf-8")

    result = run_validator(data_dir)
    assert result.returncode == 1
    assert "salaries must increase entry → mid → senior" in result.stdout


def test_loader_reads_every_file() -> None:
    dataset = load_dataset()
    assert len(dataset.cities) == len(config.CITIES)
    assert config.SCHOLARSHIPS_MIN <= len(dataset.scholarships) <= config.SCHOLARSHIPS_MAX
    assert dataset.questions_college.skills is not None
    assert dataset.questions_school.skills is None
    assert [p.id for p in dataset.demo_profiles] == ["ananya", "rahul", "meera"]


def test_schema_literals_match_config() -> None:
    assert get_args(Domain) == config.DOMAINS
    assert tuple(config.DOMAIN_MIN_CAREERS) == config.DOMAINS
    assert get_args(CityId) == config.CITIES


def test_career_rejects_missing_city_and_out_of_range_values() -> None:
    Career.model_validate(sample_career())
    demand = {c: 0.5 for c in config.CITIES if c != "mysuru"}
    with pytest.raises(ValidationError, match="mysuru"):
        Career.model_validate(sample_career(city_demand=demand))
    with pytest.raises(ValidationError):
        Career.model_validate(sample_career(growth_index=1.5))


def test_school_student_needs_stream_from_class_11() -> None:
    base = {
        "track": "school",
        "home_city": "mysuru",
        "willing_to_relocate": False,
        "wants_higher_studies": True,
        "risk_tolerance": "medium",
    }
    SchoolStudentInput.model_validate({**base, "current_class": 10})
    SchoolStudentInput.model_validate({**base, "current_class": 12, "stream": "PCM"})
    with pytest.raises(ValidationError, match="stream is required"):
        SchoolStudentInput.model_validate({**base, "current_class": 12})


def test_parent_input_rejects_unknown_values() -> None:
    parent = {
        "annual_income_inr": 700000,
        "education_budget_inr": 500000,
        "loan_willingness": "moderate",
        "risk_appetite": "medium",
        "location_preference": "near_home",
        "supports_higher_studies": True,
        "top_priority": "stability",
    }
    ParentInput.model_validate(parent)
    with pytest.raises(ValidationError):
        ParentInput.model_validate({**parent, "loan_willingness": "maybe"})
