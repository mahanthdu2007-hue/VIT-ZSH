import pytest
from factories import career, college_student, pathway, school_student

from app.engine import config
from app.engine.loader import get_dataset
from app.engine.skills import roadmap, skill_gaps, skill_plan, timeline, years_until_start
from app.models.schemas import SkillGap, StudentVector

VOCAB = {s.name: s for s in get_dataset().skills}  # Python → logical, Mathematics → numerical, Teamwork → none
CAREER = career([pathway("a"), pathway("b")], fields={"skills": [
    {"name": "Python", "importance": 0.9, "level_required": 0.8},
    {"name": "Teamwork", "importance": 0.6, "level_required": 0.6},
    {"name": "Mathematics", "importance": 0.8, "level_required": 0.75},
]})
VECTOR = StudentVector(values={d: 0.5 for d in config.STUDENT_DIMENSIONS} | {"logical": 2 / 3, "numerical": 1.0},
                       aptitude_correct={}, defaulted=[])


def gap(skill: str, value: float, current: float = 0.2, required: float = 0.8) -> SkillGap:
    return SkillGap(skill=skill, importance=1.0, level_required=required, current=current, gap=value)


def test_school_gaps_from_aptitude_and_baseline() -> None:
    # Python: current = logical 0.667 → 0.9 × (0.8 − 0.667) = 0.12
    # Teamwork: no aptitude link → baseline 0.2 → 0.6 × 0.4 = 0.24
    # Mathematics: current = numerical 1.0 → 0
    gaps = skill_gaps(CAREER, school_student(), VECTOR, VOCAB)
    assert [g.skill for g in gaps] == ["Teamwork", "Python", "Mathematics"]
    assert [g.gap for g in gaps] == pytest.approx([0.24, 0.12, 0.0])


def test_college_gaps_use_self_rating() -> None:
    # Python rated 30 → 0.9 × (0.8 − 0.3) = 0.45; Teamwork rated 80 → 0; Mathematics unrated → numerical 1.0 → 0
    student = college_student(self_rated_skills={"Python": 30, "Teamwork": 80})
    gaps = skill_gaps(CAREER, student, VECTOR, VOCAB)
    assert gaps[0].skill == "Python" and gaps[0].gap == pytest.approx(0.45)
    assert sum(g.gap for g in gaps) == pytest.approx(0.45)


def test_roadmap_interleaves_and_appends_extra_learning() -> None:
    path = pathway("p").model_copy(update={"steps": ["Class 12", "B.Tech", "Job"]})
    steps = roadmap(path, [gap("A", 0.3), gap("B", 0.2), gap("C", 0.0)])
    assert [s.text for s in steps] == ["Class 12", "Build A from 20% to 80%", "B.Tech",
                                       "Build B from 20% to 80%", "Job"]
    short = path.model_copy(update={"steps": ["Course"]})
    assert [s.skill for s in roadmap(short, [gap("A", 0.3), gap("B", 0.2)])] == [None, "A", "B"]


@pytest.mark.parametrize(
    ("student", "entry", "years"),
    [
        (school_student(12), "after_class_12", 1),
        (school_student(10), "after_class_12", 3),
        (school_student(10), "after_class_10", 1),
        (school_student(9), "after_class_10", 2),
        (college_student(year=2), "graduate", 2),
        (college_student(year=3), "graduate", 1),
    ],
)
def test_years_until_start(student, entry, years) -> None:  # type: ignore[no-untyped-def]
    assert years_until_start(pathway("p", entry=entry), student) == years


def test_timeline_spreads_pathway_steps_to_the_end_year() -> None:
    # Class 12, 4-year pathway: end = 2026 + 1 + 4 = 2031. Three pathway steps at
    # 2026, 2026 + round(0.5 × 5) = 2029, 2031; each learning step shares the year before it.
    path = pathway("p", duration=4).model_copy(update={"steps": ["Class 12", "B.Tech", "Job"]})
    steps = roadmap(path, [gap("A", 0.3), gap("B", 0.2)])
    years = timeline(steps, path, school_student(12), 2026)
    assert [(y.year, y.steps) for y in years] == [
        (2026, ["Class 12", "Build A from 20% to 80%"]),
        (2029, ["B.Tech", "Build B from 20% to 80%"]),
        (2031, ["Job"]),
    ]


def test_skill_plan_mean_gap() -> None:
    plan = skill_plan(CAREER, CAREER.pathways[0], school_student(), VECTOR, VOCAB, 2026)
    assert plan.mean_gap == pytest.approx((0.24 + 0.12 + 0.0) / 3)
    assert plan.timeline[0].year == 2026
