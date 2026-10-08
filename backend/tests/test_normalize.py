import pytest
from factories import college_student, parent, school_student

from app.engine.loader import get_dataset
from app.engine.normalize import (
    completeness,
    likert_value,
    parent_preferences,
    student_preferences,
    student_vector,
)

DATA = get_dataset()
SCHOOL_Q = DATA.questions_school
COLLEGE_Q = DATA.questions_college
PROFILES = {p.id: p for p in DATA.demo_profiles}


def test_likert_maps_one_to_five_onto_zero_to_one() -> None:
    assert [likert_value(x) for x in (1, 2, 3, 4, 5)] == [0.0, 0.25, 0.5, 0.75, 1.0]


def test_vector_all_correct_all_fives() -> None:
    student = school_student(
        aptitude_answers={i.id: i.answer for i in SCHOOL_Q.aptitude},
        riasec_answers={i.id: 5 for i in SCHOOL_Q.riasec},
        workstyle_answers={i.id: 5 for i in SCHOOL_Q.workstyle},
    )
    vector = student_vector(student, SCHOOL_Q)
    assert all(v == 1.0 for v in vector.values.values())
    assert vector.defaulted == []


def test_vector_for_ananya_matches_hand_calculation() -> None:
    # Aptitude: numerical 3/3, logical 3/3, verbal 2/3, spatial 2/3.
    # R = mean(.5, .5, .75); A = mean(.25, .5, .25); S = mean(.5, .25, .25);
    # E = mean(.5, .5, .25); C = mean(.75, .75, .5); creative = mean(ws 4 → .75, A).
    vector = student_vector(PROFILES["ananya"].student, SCHOOL_Q)
    expected = {
        "numerical": 1.0, "logical": 1.0, "verbal": 2 / 3, "spatial": 2 / 3,
        "R": 0.5833333, "I": 1.0, "A": 0.3333333, "S": 0.3333333, "E": 0.4166667, "C": 0.6666667,
        "creative": (0.75 + 1 / 3) / 2,
    }
    assert vector.values == pytest.approx(expected, abs=1e-6)
    assert list(vector.values) == ["numerical", "logical", "verbal", "spatial", "creative",
                                   "R", "I", "A", "S", "E", "C"]


def test_vector_with_missing_answers_uses_wrong_and_neutral() -> None:
    # One numerical item answered correctly, others unanswered → 1/3; spatial none → 0.
    # Only one R item answered (4 → .75); no I answers → neutral .5; no creative item → mean(.5, A).
    first_numerical = next(i for i in SCHOOL_Q.aptitude if i.dimension == "numerical")
    first_r = next(i for i in SCHOOL_Q.riasec if i.dimension == "R")
    a_items = [i.id for i in SCHOOL_Q.riasec if i.dimension == "A"]
    student = school_student(
        aptitude_answers={first_numerical.id: first_numerical.answer},
        riasec_answers={first_r.id: 4, a_items[0]: 1, a_items[1]: 3},
    )
    vector = student_vector(student, SCHOOL_Q)
    assert vector.values["numerical"] == pytest.approx(1 / 3)
    assert vector.values["spatial"] == 0.0
    assert vector.values["R"] == 0.75
    assert vector.values["I"] == 0.5
    assert vector.values["A"] == 0.25
    assert vector.values["creative"] == pytest.approx((0.5 + 0.25) / 2)
    assert set(vector.defaulted) == {"I", "S", "E", "C", "creative"}


def test_student_preferences() -> None:
    prefs = student_preferences(PROFILES["ananya"].student, SCHOOL_Q)
    assert (prefs.risk_tolerance, prefs.relocation, prefs.higher_studies) == (0.8, 1.0, 1.0)
    assert prefs.stability == 0.75
    assert prefs.marks == pytest.approx(0.92)
    blank = student_preferences(school_student(), SCHOOL_Q)
    assert (blank.stability, blank.marks) == (0.5, None)


@pytest.mark.parametrize(
    ("profile_id", "expected"),
    [
        ("ananya", (0.5, 0.0, 1.0, 1.0)),  # medium, near_home, supports, stability
        ("rahul", (0.2, 0.0, 0.0, 1.0)),   # low, near_home, does not support, stability
        ("meera", (0.5, 0.5, 1.0, 0.6)),   # medium, anywhere_india, supports, prestige
    ],
)
def test_parent_preferences(profile_id: str, expected: tuple[float, float, float, float]) -> None:
    prefs = parent_preferences(PROFILES[profile_id].parent)
    assert (prefs.risk_appetite, prefs.location, prefs.higher_studies, prefs.priority_stability) == expected


def test_completeness_full_demo_profiles_score_one() -> None:
    ananya = completeness(PROFILES["ananya"].student, PROFILES["ananya"].parent, SCHOOL_Q)
    rahul = completeness(PROFILES["rahul"].student, PROFILES["rahul"].parent, COLLEGE_Q)
    # School Class 12: 34 items + 12 student fields (incl. stream) + 9 parent fields = 55.
    # College: 34 items + 20 skills + 12 student fields + 9 parent fields = 75.
    assert (ananya.score, ananya.total, ananya.missing) == (1.0, 55, [])
    assert (rahul.score, rahul.total, rahul.missing) == (1.0, 75, [])


def test_completeness_minimal_class_10_profile() -> None:
    # Class 10 has no stream field: 34 items + 11 student fields + 9 parent fields = 54.
    # Answered: class, home city, relocate, higher studies, risk (5) + 7 required parent fields = 12.
    result = completeness(school_student(10, free_text_1="too short"), parent(500000, 100000), SCHOOL_Q)
    assert (result.answered, result.total) == (12, 54)
    assert result.score == pytest.approx(12 / 54)
    assert "free_text_1" in result.missing and "riasec:ria_i_1" in result.missing
    assert "stream" not in result.missing


def test_completeness_college_with_gaps() -> None:
    rahul = PROFILES["rahul"]
    skills = dict(list(rahul.student.self_rated_skills.items())[5:])  # drop 5 of 20 ratings
    student = rahul.student.model_copy(update={"self_rated_skills": skills, "free_text_2": ""})
    result = completeness(student, rahul.parent, COLLEGE_Q)
    assert result.score == pytest.approx(69 / 75)
    assert len(result.missing) == 6 and "free_text_2" in result.missing


def test_completeness_counts_free_text_from_fifteen_words() -> None:
    fourteen = " ".join(["word"] * 14)
    fifteen = " ".join(["word"] * 15)
    low = completeness(college_student(free_text_1=fourteen), parent(1, 0), COLLEGE_Q)
    high = completeness(college_student(free_text_1=fifteen), parent(1, 0), COLLEGE_Q)
    assert high.answered == low.answered + 1
