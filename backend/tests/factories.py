"""Small builders for engine tests. Values are chosen so expected results are easy to hand-calculate."""

from typing import Any

from app.engine import config
from app.models.schemas import (
    Career,
    CareerFinance,
    CollegeStudentInput,
    ParentInput,
    Pathway,
    SchoolStudentInput,
    Scholarship,
)

ALL_DOMAINS = list(config.DOMAINS)


def pathway(
    pathway_id: str,
    entry: str = "after_class_12",
    cost: tuple[int, int] = (200000, 400000),
    quality: float = 0.8,
    duration: float = 4,
    institution: str = "govt",
    exams: list[str] | None = None,
) -> Pathway:
    return Pathway.model_validate({
        "id": pathway_id, "label": pathway_id, "entry": entry, "steps": ["step"],
        "duration_years": duration, "cost_inr": {"min": cost[0], "max": cost[1]},
        "institution_type": institution, "entrance_exams": exams or [], "quality": quality,
    })


def career(
    pathways: list[Pathway],
    domain: str = "Technology",
    fields: dict[str, Any] | None = None,
    **requirements: float,
) -> Career:
    vector = {d: 0.5 for d in config.STUDENT_DIMENSIONS} | requirements
    if not any(p.entry == "after_class_12" for p in pathways):
        pathways = [*pathways, pathway("unused_after_12", cost=(9_000_000, 9_000_000))]
    return Career.model_validate({
        "id": "test_career", "name": "Test career", "domain": domain, "steam": ["T"],
        "summary": "Test.", "requirement_vector": vector,
        "skills": [{"name": "Python", "importance": 0.5, "level_required": 0.5}],
        "pathways": [p.model_dump() for p in pathways],
        "salary_inr_lpa": {"entry": [4, 8], "mid": [8, 16], "senior": [16, 30]},
        "growth_index": 0.5, "job_velocity": 0.5, "disruption_index": 0.5, "stability": 0.5,
        "risk_level": 0.5, "prestige": 0.5, "higher_studies_typical": False,
        "city_demand": {c: 0.5 for c in config.CITIES}, "adjacent_careers": [],
        "sources": ["test"], "data_note": "test",
    } | (fields or {}))


def finance(
    career_id: str,
    status: str = "feasible",
    financial_fit: float = 1.0,
    effective_cost: int | None = 300000,
    funding_gap: int = 0,
    chosen: str | None = "govt",
) -> CareerFinance:
    return CareerFinance(
        career_id=career_id, status=status, chosen_pathway_id=chosen, effective_cost=effective_cost,  # type: ignore[arg-type]
        financial_fit=financial_fit, funding_gap=funding_gap, budget=500000, capacity=750000, pathways=[],
    )


def scholarship(
    scholarship_id: str,
    amount: int,
    levels: list[str],
    income_max: int | None = None,
    domains: list[str] | None = None,
    restricted_to: str | None = None,
) -> Scholarship:
    return Scholarship.model_validate({
        "id": scholarship_id, "name": scholarship_id, "provider": "test",
        "income_max_inr": income_max, "levels": levels, "domains": domains or ALL_DOMAINS,
        "amount_inr_per_year": amount, "restricted_to": restricted_to, "source": "test",
    })


def school_student(current_class: int = 12, **overrides: Any) -> SchoolStudentInput:
    data: dict[str, Any] = {
        "track": "school", "current_class": current_class, "home_city": "mysuru",
        "willing_to_relocate": False, "wants_higher_studies": False, "risk_tolerance": "medium",
    }
    if current_class >= config.STREAM_FROM_CLASS:
        data["stream"] = "PCM"
    return SchoolStudentInput.model_validate(data | overrides)


def college_student(**overrides: Any) -> CollegeStudentInput:
    data: dict[str, Any] = {
        "track": "college", "degree": "B.Com", "year": 2, "home_city": "chennai",
        "willing_to_relocate": False, "wants_higher_studies": False, "risk_tolerance": "low",
    }
    return CollegeStudentInput.model_validate(data | overrides)


def parent(income: int, budget: int, loan: str = "none", **overrides: Any) -> ParentInput:
    data: dict[str, Any] = {
        "annual_income_inr": income, "education_budget_inr": budget, "loan_willingness": loan,
        "risk_appetite": "medium", "location_preference": "near_home",
        "supports_higher_studies": True, "top_priority": "stability",
    }
    return ParentInput.model_validate(data | overrides)
