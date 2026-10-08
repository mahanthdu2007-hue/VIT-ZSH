import math

import pytest
from factories import career, pathway

from app.engine import config
from app.engine.matcher import academic_alignment, centred_cosine, student_fit
from app.models.schemas import StudentVector

N = len(config.STUDENT_DIMENSIONS)
TWO_PATHS = [pathway("a"), pathway("b")]  # a career needs at least two pathways


def vector(**values: float) -> StudentVector:
    full = {d: 0.5 for d in config.STUDENT_DIMENSIONS} | values
    return StudentVector(values=full, aptitude_correct={}, defaulted=[])


def test_centred_cosine_identical_opposite_orthogonal() -> None:
    assert centred_cosine([1.0] * N, [1.0] * N) == pytest.approx(1.0)
    assert centred_cosine([1.0] * N, [0.0] * N) == pytest.approx(0.0)
    s = [1.0] + [0.5] * (N - 1)          # centred: (0.5, 0, 0, …)
    r = [0.5, 1.0] + [0.5] * (N - 2)     # centred: (0, 0.5, 0, …)
    assert centred_cosine(s, r) == pytest.approx(0.5)


def test_centred_cosine_hand_case() -> None:
    # centred S = (0.5, 0.5, 0…), centred R = (0.5, 0, 0…): cos = 0.25 / (√0.5 × 0.5) = 0.7071
    s = [1.0, 1.0] + [0.5] * (N - 2)
    r = [1.0] + [0.5] * (N - 1)
    assert centred_cosine(s, r) == pytest.approx((1 / math.sqrt(2) + 1) / 2)


def test_centred_cosine_all_neutral_is_half() -> None:
    assert centred_cosine([0.5] * N, [0.9] * N) == 0.5


def test_centring_discriminates_where_raw_cosine_does_not() -> None:
    # Raw cosine of (0.9, 0.6) vs (0.6, 0.9) is 0.92; centred they point in different directions.
    s = [0.9, 0.6] + [0.5] * (N - 2)
    r = [0.6, 0.9] + [0.5] * (N - 2)
    assert centred_cosine(s, r) < 0.75


@pytest.mark.parametrize(
    ("marks", "numerical", "verbal", "expected"),
    [
        (0.88, 0.65, 0.65, 1 - 0.65 * 0.12),   # 0.922
        (0.60, 0.9, 0.5, 1 - 0.7 * 0.40),      # 0.72
        (1.00, 0.9, 0.9, 1.0),                 # top marks → full alignment
        (None, 0.4, 0.6, 1 - 0.5 * 0.5),       # no marks → neutral 0.5 → 0.75
    ],
)
def test_academic_alignment_blend(marks, numerical, verbal, expected) -> None:  # type: ignore[no-untyped-def]
    c = career(TWO_PATHS, numerical=numerical, verbal=verbal)
    assert academic_alignment(marks, c) == pytest.approx(expected)


def test_student_fit_hand_case_one() -> None:
    # Student = career requirements → cos 1.0; affinity 0.7; alignment 1 − 0.9 × 0.08 = 0.928.
    # SF = 0.6 × 1.0 + 0.25 × 0.7 + 0.15 × 0.928 = 0.9142
    c = career(TWO_PATHS, numerical=0.9, verbal=0.9, I=0.9, A=0.1)
    s = vector(numerical=0.9, verbal=0.9, I=0.9, A=0.1)
    result = student_fit(s, c, {"Technology": 0.7}, 0.92)
    assert result.centred_cosine == pytest.approx(1.0)
    assert result.academic_alignment == pytest.approx(0.928)
    assert result.student_fit == pytest.approx(0.9142)


def test_student_fit_hand_case_two() -> None:
    # Opposite profile → cos 0; affinity 0.2; career num/verbal 0.5 → alignment 1 − 0.5 × 0.4 = 0.8.
    # SF = 0 + 0.25 × 0.2 + 0.15 × 0.8 = 0.17
    c = career(TWO_PATHS, domain="Health", R=0.9, S=0.9)
    s = vector(R=0.1, S=0.1)
    result = student_fit(s, c, {"Health": 0.2}, 0.6)
    assert result.centred_cosine == pytest.approx(0.0)
    assert result.student_fit == pytest.approx(0.17)


def test_student_fit_hand_case_three_missing_domain_affinity() -> None:
    # Orthogonal → cos 0.5; domain not in the affinity dict → 0; no marks → alignment 0.75.
    # SF = 0.6 × 0.5 + 0 + 0.15 × 0.75 = 0.4125
    c = career(TWO_PATHS, domain="Arts & Design", A=1.0, numerical=0.5, verbal=0.5)
    s = vector(I=1.0)
    result = student_fit(s, c, {"Technology": 0.9}, None)
    assert result.centred_cosine == pytest.approx(0.5)
    assert result.domain_affinity == 0.0
    assert result.student_fit == pytest.approx(0.4125)
