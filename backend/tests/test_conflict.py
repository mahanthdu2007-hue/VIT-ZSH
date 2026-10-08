import pytest
from factories import career, parent, pathway

from app.engine.conflict import (
    concern_weights,
    conflict_index,
    middle_path,
    parent_alignment,
    student_top_domains,
)
from app.engine.normalize import parent_preferences
from app.models.schemas import ParentPreferences, StudentPreferences

TWO_PATHS = [pathway("a"), pathway("b")]


def student_prefs(risk: float, relocation: float, higher: float, stability: float) -> StudentPreferences:
    return StudentPreferences(risk_tolerance=risk, relocation=relocation, higher_studies=higher,
                              stability=stability, marks=0.9)


def parent_prefs(risk: float, location: float, higher: float, priority: float) -> ParentPreferences:
    return ParentPreferences(risk_appetite=risk, location=location, higher_studies=higher,
                             priority_stability=priority)


def points(result, name):  # type: ignore[no-untyped-def]
    return next(d.points for d in result.dimensions if d.name == name)


# ---------------------------------------------------------------- Conflict Index
def test_identical_preferences_give_zero() -> None:
    affinity = {"Technology": 0.9, "Engineering": 0.7, "Science": 0.5, "Health": 0.0}
    p = parent(700000, 500000, preferred_domains=["Technology", "Engineering", "Science"])
    result = conflict_index(student_prefs(0.5, 0.0, 1.0, 1.0), parent_prefs(0.5, 0.0, 1.0, 1.0),
                            p, affinity, top_career_cost=300000)
    assert result.index == 0.0
    assert result.hotspots == []
    assert all(d.mismatch == 0 for d in result.dimensions)


def test_fully_opposed_preferences() -> None:
    # domain 1 × 25 + risk |0.8 − 0.2| = 0.6 × 15 + location 1 × 15 + higher studies 1 × 15
    # + cost clip((10,00,000 − 5,00,000)/5,00,000) = 1 × 15 + stability |0 − 1| × 15 = 94.0
    p = parent(700000, 500000, preferred_domains=["Health"])
    result = conflict_index(student_prefs(0.8, 1.0, 1.0, 0.0), parent_prefs(0.2, 0.0, 0.0, 1.0),
                            p, {"Arts & Design": 0.9}, top_career_cost=1000000)
    assert result.index == pytest.approx(94.0)
    assert points(result, "risk") == pytest.approx(9.0)
    # domain (25) first; four dimensions tie at 15, so the §7.6 order picks location.
    assert result.hotspots == ["domain", "location"]


def test_ananya_like_case() -> None:
    # domain: top-3 {Tech, Eng, Science} vs {Tech, Eng} → Jaccard 2/3 → 1/3 × 25 = 8.333
    # risk |0.8 − 0.5| × 15 = 4.5; location |1 − 0| × 15 = 15; higher studies 0;
    # cost 3,50,000 ≤ 5,00,000 → 0; stability |0.75 − 1.0| × 15 = 3.75. Total 31.583.
    affinity = {"Technology": 0.9, "Engineering": 0.6, "Science": 0.4, "Health": 0.1}
    p = parent(700000, 500000, preferred_domains=["Technology", "Engineering"])
    result = conflict_index(student_prefs(0.8, 1.0, 1.0, 0.75), parent_prefs(0.5, 0.0, 1.0, 1.0),
                            p, affinity, top_career_cost=350000)
    assert points(result, "domain") == pytest.approx(25 / 3)
    assert result.index == pytest.approx(15 + 25 / 3 + 4.5 + 3.75)
    assert result.hotspots == ["location", "domain"]
    assert result.student_top_domains == ["Technology", "Engineering", "Science"]


def test_cost_mismatch_partial_and_zero_budget() -> None:
    same = (student_prefs(0.5, 0.0, 1.0, 1.0), parent_prefs(0.5, 0.0, 1.0, 1.0))
    partial = conflict_index(*same, parent(700000, 400000), {}, top_career_cost=500000)
    assert points(partial, "cost") == pytest.approx(15 * 0.25)  # (5L − 4L)/4L = 0.25
    zero = conflict_index(*same, parent(700000, 0), {}, top_career_cost=100000)
    assert points(zero, "cost") == pytest.approx(15.0)


def test_no_domain_preference_means_no_domain_conflict() -> None:
    same = (student_prefs(0.5, 0.0, 1.0, 1.0), parent_prefs(0.5, 0.0, 1.0, 1.0))
    result = conflict_index(*same, parent(700000, 500000), {"Arts & Design": 0.9}, 0)
    assert points(result, "domain") == 0.0


def test_student_top_domains_ignore_zero_and_break_ties_by_domain_order() -> None:
    affinity = {"Health": 0.5, "Technology": 0.5, "Science": 0.9, "Arts & Design": 0.0, "Engineering": 0.2}
    assert student_top_domains(affinity) == ["Science", "Technology", "Health"]


# ---------------------------------------------------------------- Parent Alignment
CAREER = career(TWO_PATHS)  # Technology; risk, stability, prestige 0.5; all city demand 0.5; entry 4–8 LPA


def test_concern_weights_boost_and_renormalise() -> None:
    weights = concern_weights({"financial burden": 0.8, "job security": 0.4})
    assert weights["financial_fit"] == pytest.approx(0.3 / 1.1)
    assert weights["risk"] == pytest.approx(0.2 / 1.1)
    assert sum(weights.values()) == pytest.approx(1.0)
    assert concern_weights({}) == pytest.approx({k: 0.2 for k in weights})


def test_parent_alignment_case_one_stability_near_home() -> None:
    # domain 1.0, risk 1 − |0.5 − 0.5| = 1, location (near_home) 0.5, priority stability 0.5, FF 0.9
    # equal weights → (1 + 1 + 0.5 + 0.5 + 0.9) / 5 = 0.78
    p = parent(700000, 500000, preferred_domains=["Technology"])
    result = parent_alignment(CAREER, p, parent_preferences(p), "mysuru", 0.7, 0.9, 1200000, concern_weights({}))
    assert result.components == pytest.approx(
        {"domain": 1.0, "risk": 1.0, "location": 0.5, "priority": 0.5, "financial_fit": 0.9})
    assert result.parent_alignment == pytest.approx(0.78)


def test_parent_alignment_case_two_happiness_anywhere() -> None:
    # domain not preferred 0.3, risk 1 − |0.5 − 0.2| = 0.7, location (anywhere) 1.0,
    # priority happiness = SF 0.7, FF 1.0 → (0.3 + 0.7 + 1 + 0.7 + 1) / 5 = 0.74
    p = parent(700000, 500000, preferred_domains=["Health"], risk_appetite="low",
               location_preference="anywhere_india", top_priority="happiness")
    result = parent_alignment(CAREER, p, parent_preferences(p), "mysuru", 0.7, 1.0, 1200000, concern_weights({}))
    assert result.parent_alignment == pytest.approx(0.74)


def test_parent_alignment_case_three_salary_priority_with_concern() -> None:
    # priority salary: entry mid 6,00,000 / max 12,00,000 = 0.5. Components as case one.
    # Weights with financial-burden concern: FF 0.3/1.1, others 0.2/1.1.
    # PA = (1 + 1 + 0.5 + 0.5) × 0.2/1.1 + 0.9 × 0.3/1.1 = 0.7909
    p = parent(700000, 500000, preferred_domains=["Technology"], top_priority="salary")
    weights = concern_weights({"financial burden": 0.9})
    result = parent_alignment(CAREER, p, parent_preferences(p), "mysuru", 0.7, 0.9, 1200000, weights)
    assert result.components["priority"] == pytest.approx(0.5)
    assert result.parent_alignment == pytest.approx((3.0 * 0.2 + 0.9 * 0.3) / 1.1)


# ---------------------------------------------------------------- Nash middle path
U_S = {"a": 0.9, "b": 0.7, "c": 0.5, "d": 0.3, "e": 0.1}
U_P = {"a": 0.1, "b": 0.6, "c": 0.5, "d": 0.9, "e": 0.2}
ALL_FEASIBLE = {c: "feasible" for c in U_S}


def test_nash_middle_path_hand_case() -> None:
    # d = (median U_s, median U_p) = (0.5, 0.5). Only b has both terms > 0: (0.2)(0.1) = 0.02.
    result = middle_path(U_S, U_P, ALL_FEASIBLE)  # type: ignore[arg-type]
    assert result is not None
    assert (result.career_id, result.method) == ("b", "nash")
    assert (result.disagreement_s, result.disagreement_p) == (0.5, 0.5)
    assert result.candidates[0].product == pytest.approx(0.02)
    assert (result.student_top_career_id, result.parent_top_career_id) == ("a", "d")
    assert result.student_change == pytest.approx(-0.2) and result.parent_change == pytest.approx(-0.3)
    assert result.student_gain == pytest.approx(0.2) and result.parent_gain == pytest.approx(0.1)


def test_nash_picks_largest_product_and_ignores_needs_aid() -> None:
    # f is best for both sides but needs aid: excluded from the medians and the candidates.
    # Medians over a–e and g: U_s [0.9,0.7,0.5,0.3,0.1,0.8] → 0.6; U_p [0.1,0.6,0.5,0.9,0.2,0.8] → 0.55.
    # b: (0.1)(0.05) = 0.005; g: (0.2)(0.25) = 0.05 → g.
    u_s = U_S | {"f": 0.95, "g": 0.8}
    u_p = U_P | {"f": 0.95, "g": 0.8}
    statuses = ALL_FEASIBLE | {"f": "needs_aid", "g": "feasible"}
    result = middle_path(u_s, u_p, statuses)  # type: ignore[arg-type]
    assert result is not None and result.career_id == "g"
    assert result.disagreement_s == pytest.approx(0.6) and result.disagreement_p == pytest.approx(0.55)
    assert [c.career_id for c in result.candidates] == ["g", "b"]


def test_nash_fallback_to_highest_minimum() -> None:
    # Perfectly opposed: no career beats both medians; min(U_s, U_p) is highest for c (0.5).
    u_p = {"a": 0.1, "b": 0.3, "c": 0.5, "d": 0.7, "e": 0.9}
    result = middle_path(U_S, u_p, ALL_FEASIBLE)  # type: ignore[arg-type]
    assert result is not None
    assert (result.career_id, result.method, result.candidates) == ("c", "max_min", [])


def test_nash_without_feasible_careers_returns_none() -> None:
    assert middle_path(U_S, U_P, {c: "needs_aid" for c in U_S}) is None  # type: ignore[arg-type]
