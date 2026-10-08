"""Hypothesis strategies that build valid random inputs from the §6 input models and the real question sets."""

from datetime import date
from typing import Any

from hypothesis import strategies as st

from app.engine import config
from app.engine.loader import get_dataset
from app.engine.system1 import build_decision
from app.models.schemas import (
    CollegeStudentInput,
    ParentInput,
    QuestionSet,
    SchoolStudentInput,
    StudentInput,
    TypedDecision,
)

DATA = get_dataset()
AS_OF = date(2026, 10, 8)  # fixed "today" so timelines and next exams are reproducible
STAND_IN_BACKEND = "stand_in"
CAREER_IDS = [c.id for c in DATA.careers]
LEVELS = ["low", "medium", "high"]
STREAMS = ["PCM", "PCB", "PCMB", "Commerce", "Humanities"]
MAX_INCOME_INR = 50_000_000
MAX_BUDGET_INR = 20_000_000
WORDS = st.sampled_from(["I", "love", "building", "things", "with", "code", "and", "art", "people", "help"])

unit = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
free_text = st.lists(WORDS, max_size=30).map(" ".join)


def _subset_dict(ids: list[str], values: st.SearchStrategy[int]) -> st.SearchStrategy[dict[str, int]]:
    """Answers for a random subset of items, so partly answered questionnaires are covered too."""
    return st.fixed_dictionaries({}, optional={i: values for i in ids})


@st.composite
def _common(draw: st.DrawFn, questions: QuestionSet) -> dict[str, Any]:
    likert = st.integers(config.LIKERT_MIN, config.LIKERT_MAX)
    aptitude = st.fixed_dictionaries({}, optional={
        item.id: st.integers(0, len(item.options) - 1) for item in questions.aptitude
    })
    return {
        "aptitude_answers": draw(aptitude),
        "riasec_answers": draw(_subset_dict([i.id for i in questions.riasec], likert)),
        "workstyle_answers": draw(_subset_dict([i.id for i in questions.workstyle], likert)),
        "marks_percent": draw(st.none() | st.floats(0.0, config.MARKS_MAX, allow_nan=False)),
        "favourite_subjects": draw(st.lists(st.sampled_from(["Mathematics", "Biology", "Art", "History"]),
                                            max_size=3, unique=True)),
        "home_city": draw(st.sampled_from(config.CITIES)),
        "preferred_cities": draw(st.lists(st.sampled_from(config.CITIES), max_size=4, unique=True)),
        "willing_to_relocate": draw(st.booleans()),
        "wants_higher_studies": draw(st.booleans()),
        "risk_tolerance": draw(st.sampled_from(LEVELS)),
        "dream_career_id": draw(st.none() | st.sampled_from(CAREER_IDS)),
        "free_text_1": draw(free_text),
        "free_text_2": draw(free_text),
    }


@st.composite
def school_students(draw: st.DrawFn) -> SchoolStudentInput:
    data = draw(_common(DATA.questions_school))
    current_class = draw(st.integers(config.SCHOOL_CLASS_MIN, config.SCHOOL_CLASS_MAX))
    stream = draw(st.sampled_from(STREAMS)) if current_class >= config.STREAM_FROM_CLASS else None
    return SchoolStudentInput.model_validate(data | {"track": "school", "current_class": current_class,
                                                     "stream": stream})


@st.composite
def college_students(draw: st.DrawFn) -> CollegeStudentInput:
    data = draw(_common(DATA.questions_college))
    skills = _subset_dict(DATA.questions_college.skills or [], st.integers(0, int(config.SKILL_RATING_SCALE)))
    return CollegeStudentInput.model_validate(data | {
        "track": "college",
        "degree": draw(st.sampled_from(["B.Com", "B.Sc", "B.A.", "B.Tech"])),
        "year": draw(st.integers(config.COLLEGE_YEAR_MIN, config.COLLEGE_YEAR_MAX)),
        "self_rated_skills": draw(skills),
    })


students: st.SearchStrategy[StudentInput] = st.one_of(school_students(), college_students())


@st.composite
def parents(draw: st.DrawFn) -> ParentInput:
    return ParentInput.model_validate({
        "annual_income_inr": draw(st.integers(1, MAX_INCOME_INR)),
        "education_budget_inr": draw(st.integers(0, MAX_BUDGET_INR)),
        "loan_willingness": draw(st.sampled_from(list(config.LOAN_FACTOR))),
        "risk_appetite": draw(st.sampled_from(LEVELS)),
        "preferred_domains": draw(st.lists(st.sampled_from(config.DOMAINS), max_size=3, unique=True)),
        "location_preference": draw(st.sampled_from(list(config.LOCATION_PREFERENCE_VALUE))),
        "supports_higher_studies": draw(st.booleans()),
        "top_priority": draw(st.sampled_from(list(config.PRIORITY_STABILITY_VALUE))),
        "free_text": draw(free_text),
    })


domain_affinities = st.fixed_dictionaries({d: unit for d in config.DOMAINS})
concern_probabilities = st.fixed_dictionaries({c: unit for c in config.PARENT_CONCERNS})


@st.composite
def profiles(draw: st.DrawFn) -> tuple[StudentInput, ParentInput, dict[str, float], dict[str, float]]:
    """One full random profile: student, parent, and stand-in System 1 probabilities."""
    return draw(students), draw(parents()), draw(domain_affinities), draw(concern_probabilities)


def stand_in_decisions(domain_affinity: dict[str, float], concerns: dict[str, float]) -> list[TypedDecision]:
    """System 1 decisions with given probabilities, so engine tests do not depend on a model."""
    return [
        build_decision(config.DECISION_STUDENT_DOMAIN, dict(domain_affinity), STAND_IN_BACKEND),
        build_decision(config.DECISION_PARENT_CONCERNS, dict(concerns), STAND_IN_BACKEND),
    ]
