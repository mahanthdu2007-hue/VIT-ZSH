from factories import career, finance, pathway, scholarship, school_student

from app.engine import config
from app.engine.loader import get_dataset
from app.engine.swot import months_until, swot
from app.models.schemas import ConflictDimension, ConflictResult, SkillGap, StudentVector

DATA = get_dataset()
EXAMS = {e.id: e for e in DATA.exams}
CITY_NAMES = {c.id: c.name for c in DATA.cities}

DEMAND_A = {c: 0.3 for c in config.CITIES} | {"bengaluru": 0.95, "hyderabad": 0.85}
DEMAND_B = {c: 0.3 for c in config.CITIES} | {"bengaluru": 0.9, "hyderabad": 0.6}
GOVT = pathway("govt", exams=["kcet", "jee_main", "nata"])  # April, January, April
TOP = career([GOVT, pathway("other")], fields={"id": "top", "name": "Top career", "city_demand": DEMAND_A,
                                                "disruption_index": 0.25})
SECOND = career([GOVT, pathway("other")], fields={"id": "second", "name": "Second career", "city_demand": DEMAND_B})
STUDENT = school_student(willing_to_relocate=True, preferred_cities=["bengaluru", "hyderabad"])
VECTOR = StudentVector(values={d: 0.5 for d in config.STUDENT_DIMENSIONS}
                       | {"numerical": 1.0, "logical": 1.0, "I": 1.0, "spatial": 0.9},
                       aptitude_correct={}, defaulted=[])
GAPS = [SkillGap(skill=s, importance=1, level_required=0.8, current=0.2, gap=g)
        for s, g in [("Python", 0.4), ("Statistics", 0.3), ("Cloud computing", 0.2), ("SQL", 0.1), ("Maths", 0.0)]]
SCHOLARSHIPS = [
    scholarship("small_open", 10000, ["ug"], income_max=800000),
    scholarship("big_restricted", 50000, ["ug"], income_max=800000, restricted_to="girls"),
    scholarship("mid_open", 20000, ["ug"]),
    scholarship("tiny_open", 5000, ["ug"]),
    scholarship("pg_only", 90000, ["pg"]),
    scholarship("low_income", 80000, ["ug"], income_max=300000),
]
CONFLICT = ConflictResult(index=31.6, hotspots=["location", "domain"], student_top_domains=[], dimensions=[
    ConflictDimension(name="location", weight=0.15, student_value=1, parent_value=0, mismatch=1, points=15),
    ConflictDimension(name="domain", weight=0.25, student_value=None, parent_value=None, mismatch=1 / 3,
                      points=25 / 3),
])


def build(funding_gap: int = 0, conflict: ConflictResult = CONFLICT):  # type: ignore[no-untyped-def]
    return swot(VECTOR, GAPS, [TOP, SECOND], STUDENT, CITY_NAMES, finance("top", funding_gap=funding_gap),
                SCHOLARSHIPS, 700000, EXAMS, current_month=10, conflict=conflict)


def test_months_until_wraps_around_the_year() -> None:
    assert months_until("January", 10) == 3
    assert months_until("October", 10) == 0
    assert months_until("April", 10) == 6


def test_strengths_are_top_three_dimensions_in_order() -> None:
    # numerical, logical and I all 1.0 → kept in §7.2 order; spatial 0.9 is fourth.
    assert [(s.label, s.value) for s in build().strengths] == [("numerical", 1.0), ("logical", 1.0), ("I", 1.0)]


def test_weaknesses_are_top_three_positive_gaps() -> None:
    assert [w.label for w in build().weaknesses] == ["Python", "Statistics", "Cloud computing"]


def test_opportunities_cities_scholarships_and_next_exams() -> None:
    items = build().opportunities
    cities = [(o.label, o.value) for o in items if o.kind == "city_demand"]
    assert cities == [("Top career in Bengaluru", 0.95), ("Second career in Bengaluru", 0.9),
                      ("Top career in Hyderabad", 0.85)]
    # UG schemes the income of 7,00,000 qualifies for (restricted ones included), largest first.
    assert [o.label for o in items if o.kind == "scholarship"] == ["big_restricted", "mid_open", "small_open"]
    # From October: JEE Main (January) in 3 months, then KCET and NATA (April) in 6.
    exams = [(o.label.split(" (")[0], o.value) for o in items if o.kind == "exam"]
    assert [v for _, v in exams] == [3, 6, 6]
    assert exams[0][0].startswith("Joint Entrance Examination Main")


def test_threats_include_gap_only_when_positive() -> None:
    without_gap = build().threats
    assert [(t.kind, t.value) for t in without_gap] == [("disruption", 0.25), ("conflict", 15)]
    with_gap = build(funding_gap=52000).threats
    assert ("funding_gap", 52000) in [(t.kind, t.value) for t in with_gap]


def test_threats_without_conflict_hotspot() -> None:
    calm = ConflictResult(index=0, hotspots=[], student_top_domains=[], dimensions=[])
    assert [t.kind for t in build(conflict=calm).threats] == ["disruption"]
