import pytest
from factories import college_student, parent, school_student

from app.engine.loader import get_dataset
from app.engine.normalize import (
    completeness,
    likert_value,
    parent_preferences,
    question_set_id,
    student_preferences,
    student_vector,
)

DATA = get_dataset()
SCHOOL_Q = DATA.question_sets["class_11_12_science"]  # the factory's default student is Class 12 PCM
CLASS_10_Q = DATA.question_sets["class_9_10"]
COLLEGE_Q = DATA.question_sets["college"]
PROFILES = {p.id: p for p in DATA.demo_profiles}


@pytest.mark.parametrize(
    ("track", "stream", "expected"),
    [
        ("school", None, "class_9_10"),
        ("school", "PCM", "class_11_12_science"),
        ("school", "PCB", "class_11_12_science"),
        ("school", "PCMB", "class_11_12_science"),
        ("school", "Commerce", "class_11_12_commerce"),
        ("school", "Humanities", "class_11_12_humanities"),
        ("college", None, "college"),
    ],
)
def test_question_set_follows_the_students_path(track: str, stream: str | None, expected: str) -> None:
    assert question_set_id(track, stream) == expected  # type: ignore[arg-type]


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
    # Aptitude: numerical 2/2, logical 2/2, verbal 1/2, spatial 1/2.
    # RIASEC answers 3, 5, 2, 2, 3, 4 → (x − 1)/4; creative = mean(ws 4 → .75, A .25).
    vector = student_vector(PROFILES["ananya"].student, SCHOOL_Q)
    expected = {
        "numerical": 1.0, "logical": 1.0, "verbal": 0.5, "spatial": 0.5,
        "R": 0.5, "I": 1.0, "A": 0.25, "S": 0.25, "E": 0.5, "C": 0.75,
        "creative": (0.75 + 0.25) / 2,
    }
    assert vector.values == pytest.approx(expected, abs=1e-6)
    assert list(vector.values) == ["numerical", "logical", "verbal", "spatial", "creative",
                                   "R", "I", "A", "S", "E", "C"]


def test_vector_with_missing_answers_uses_wrong_and_neutral() -> None:
    # One numerical item answered correctly, the other unanswered → 1/2; spatial none → 0.
    # R answered 4 → .75; A answered 2 → .25; no I answer → neutral .5; no creative item → mean(.5, A).
    first_numerical = next(i for i in SCHOOL_Q.aptitude if i.dimension == "numerical")
    r_item = next(i for i in SCHOOL_Q.riasec if i.dimension == "R")
    a_item = next(i for i in SCHOOL_Q.riasec if i.dimension == "A")
    student = school_student(
        aptitude_answers={first_numerical.id: first_numerical.answer},
        riasec_answers={r_item.id: 4, a_item.id: 2},
    )
    vector = student_vector(student, SCHOOL_Q)
    assert vector.values["numerical"] == pytest.approx(1 / 2)
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
    # School Class 12: 16 items + 12 student fields (incl. stream) + 9 parent fields = 37.
    # College: 16 items + 10 skills + 12 student fields + 9 parent fields = 47.
    assert (ananya.score, ananya.total, ananya.missing) == (1.0, 37, [])
    assert (rahul.score, rahul.total, rahul.missing) == (1.0, 47, [])


def test_completeness_minimal_class_10_profile() -> None:
    # Class 10 has no stream field: 16 items + 11 student fields + 9 parent fields = 36.
    # Answered: class, home city, relocate, higher studies, risk (5) + 7 required parent fields = 12.
    result = completeness(school_student(10, free_text_1="too short"), parent(500000, 100000), CLASS_10_Q)
    assert (result.answered, result.total) == (12, 36)
    assert result.score == pytest.approx(12 / 36)
    assert "free_text_1" in result.missing and "riasec:c910_i" in result.missing
    assert "stream" not in result.missing


def test_completeness_college_with_gaps() -> None:
    rahul = PROFILES["rahul"]
    skills = dict(list(rahul.student.self_rated_skills.items())[5:])  # drop 5 of 10 ratings
    student = rahul.student.model_copy(update={"self_rated_skills": skills, "free_text_2": ""})
    result = completeness(student, rahul.parent, COLLEGE_Q)
    assert result.score == pytest.approx(41 / 47)
    assert len(result.missing) == 6 and "free_text_2" in result.missing


def test_completeness_counts_free_text_from_fifteen_words() -> None:
    fourteen = " ".join(["word"] * 14)
    fifteen = " ".join(["word"] * 15)
    low = completeness(college_student(free_text_1=fourteen), parent(1, 0), COLLEGE_Q)
    high = completeness(college_student(free_text_1=fifteen), parent(1, 0), COLLEGE_Q)
    assert high.answered == low.answered + 1
