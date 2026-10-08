import math

import pytest
from factories import career, finance, pathway, school_student

from app.engine.scoring import (
    confidence,
    entry_mid_inr,
    growth,
    prism_score,
    rank_top_careers,
    risk_radar,
)
from app.models.schemas import Completeness, MarketDemand, TypedDecision

TWO_PATHS = [pathway("a"), pathway("b")]


def salary_career(entry, senior, growth_index):  # type: ignore[no-untyped-def]
    mid = [(e + s) / 2 for e, s in zip(entry, senior)]
    return career(TWO_PATHS, fields={"growth_index": growth_index,
                                     "salary_inr_lpa": {"entry": entry, "mid": mid, "senior": senior}})


def decision(question_id: str, conf: float, abstained: bool = False) -> TypedDecision:
    return TypedDecision(question_id=question_id, choice=None if abstained else "x", probabilities={},
                         confidence=conf, margin=0.2, abstained=abstained, backend="test")


# ---------------------------------------------------------------- Growth
def test_entry_mid_inr() -> None:
    assert entry_mid_inr(salary_career([6, 12], [30, 60], 0.5)) == 900000


def test_growth_case_one() -> None:
    # trajectory = (45/9 − 1)/5 = 0.8; mobility = log2(9,00,000/7,00,000)/3 = 0.12086
    # G = 0.5 × 0.85 + 0.3 × 0.8 + 0.2 × 0.12086 = 0.68917
    result = growth(salary_career([6, 12], [30, 60], 0.85), 700000)
    assert result.trajectory == pytest.approx(0.8)
    assert result.mobility_uplift == pytest.approx(math.log2(9 / 7) / 3)
    assert result.growth == pytest.approx(0.425 + 0.24 + 0.2 * math.log2(9 / 7) / 3)


def test_growth_case_two_trajectory_capped_mobility_floored() -> None:
    # trajectory (30/3 − 1)/5 = 1.8 → 1; mobility log2(3,00,000/40,00,000) < 0 → 0; G = 0.25 + 0.3 = 0.55
    result = growth(salary_career([2, 4], [20, 40], 0.5), 4000000)
    assert (result.trajectory, result.mobility_uplift) == (1.0, 0.0)
    assert result.growth == pytest.approx(0.55)


def test_growth_case_three_mobility_capped() -> None:
    # trajectory (20/10 − 1)/5 = 0.2; mobility log2(10,00,000/1,00,000)/3 = 1.107 → 1; G = 0.3 + 0.06 + 0.2
    result = growth(salary_career([8, 12], [16, 24], 0.6), 100000)
    assert result.mobility_uplift == 1.0
    assert result.growth == pytest.approx(0.56)


# ---------------------------------------------------------------- PRISM score
def test_prism_score_exact() -> None:
    # 30 × 0.8 + 20 × 1 + 20 × 0.7 + 15 × 0.6 + 15 × 0.5 = 24 + 20 + 14 + 9 + 7.5 = 74.5
    values = {"student_fit": 0.8, "financial_fit": 1.0, "market_demand": 0.7, "growth": 0.6,
              "parent_alignment": 0.5}
    result = prism_score("x", values)
    assert result.score == 74.5
    assert result.points == {"student_fit": 24.0, "financial_fit": 20.0, "market_demand": 14.0,
                             "growth": 9.0, "parent_alignment": 7.5}


def test_prism_score_points_sum_to_rounded_score() -> None:
    # Raw points 26.499, 18.0, 15.554, 9.1665, 6.666 → total 75.8855 → 75.9.
    # Tenths by largest remainder: 26.5, 18.0, 15.5, 9.2, 6.7 (sum 75.9).
    values = {"student_fit": 0.8833, "financial_fit": 0.9, "market_demand": 0.7777, "growth": 0.6111,
              "parent_alignment": 0.4444}
    result = prism_score("x", values)
    assert result.score == 75.9
    assert result.points == {"student_fit": 26.5, "financial_fit": 18.0, "market_demand": 15.5,
                             "growth": 9.2, "parent_alignment": 6.7}
    assert sum(result.points.values()) == pytest.approx(result.score)


def test_prism_score_bounds() -> None:
    zero = {k: 0.0 for k in ("student_fit", "financial_fit", "market_demand", "growth", "parent_alignment")}
    assert prism_score("x", zero).score == 0.0
    assert prism_score("x", {k: 1.0 for k in zero}).score == 100.0


# ---------------------------------------------------------------- Confidence
CAREER = career(TWO_PATHS)  # sources and skills present, no adjacent careers → data completeness 3/4


def completeness(score: float, missing: list[str] | None = None) -> Completeness:
    return Completeness(score=score, answered=0, total=0, missing=missing or [])


def test_confidence_high() -> None:
    # 100 × (0.4 × 0.9 + 0.35 × mean(0.8, 0.6) + 0.25 × 0.75) = 79.25
    decisions = [decision("student_domain_affinity", 0.8), decision("parent_concerns", 0.6)]
    result = confidence(completeness(0.9), decisions, CAREER, school_student())
    assert result.data_completeness == 0.75
    assert result.score == pytest.approx(79.25)
    assert result.band == "High"


def test_confidence_all_abstained_uses_point_three_and_lists_inputs() -> None:
    # 100 × (0.36 + 0.35 × 0.3 + 0.1875) = 65.25
    decisions = [decision("student_domain_affinity", 0.3, True), decision("parent_concerns", 0.4, True)]
    result = confidence(completeness(0.9, ["marks_percent"]), decisions, CAREER, school_student())
    assert result.system1_confidence == 0.3
    assert result.score == pytest.approx(65.25)
    assert result.band == "Medium"
    assert result.missing_inputs == ["marks_percent", "free_text_1", "free_text_2", "parent.free_text"]


def test_confidence_low() -> None:
    # 100 × (0.4 × 0.2 + 0.105 + 0.1875) = 37.25
    result = confidence(completeness(0.2), [], CAREER, school_student())
    assert result.score == pytest.approx(37.25)
    assert result.band == "Low"


# ---------------------------------------------------------------- Risk radar
def test_risk_radar_low_home_demand_not_relocating() -> None:
    market = MarketDemand(career_id="x", local_demand=0.35, best_city="mysuru", market_demand=0.565)
    demand = {"mysuru": 0.35} | {c: 0.5 for c in ("bengaluru", "chennai", "hyderabad", "pune",
                                                   "delhi_ncr", "mumbai", "coimbatore")}
    c = career(TWO_PATHS, fields={"city_demand": demand, "disruption_index": 0.25})
    result = risk_radar(c, finance("x", financial_fit=0.9, effective_cost=350000), market, 0.2,
                        school_student(home_city="mysuru"), 700000)
    # financial 0.1; market 0.435; location 1 (0.35 < 0.4, not relocating); cost 3.5L/7L/4 = 0.125
    assert result.financial == pytest.approx(0.1)
    assert result.market == pytest.approx(0.435)
    assert (result.location, result.skill_gap, result.disruption) == (1.0, 0.2, 0.25)
    assert result.education_cost == pytest.approx(0.125)


def test_risk_radar_relocating_and_needs_aid() -> None:
    market = MarketDemand(career_id="x", local_demand=0.95, best_city="bengaluru", market_demand=0.865)
    result = risk_radar(CAREER, finance("x", "needs_aid", 0.0, effective_cost=None), market, 0.0,
                        school_student(willing_to_relocate=True), 700000)
    assert result.location == pytest.approx(0.05)
    assert (result.financial, result.education_cost) == (1.0, 1.0)


def test_risk_radar_education_cost_is_capped() -> None:
    market = MarketDemand(career_id="x", local_demand=0.5, best_city="mysuru", market_demand=0.5)
    result = risk_radar(CAREER, finance("x", effective_cost=5000000), market, 0.0, school_student(), 400000)
    assert result.education_cost == 1.0


# ---------------------------------------------------------------- Ranking
def test_rank_top_careers_excludes_needs_aid_and_no_pathway() -> None:
    values = {"student_fit": 0.5, "financial_fit": 0.5, "market_demand": 0.5, "growth": 0.5, "parent_alignment": 0.5}
    scores = [prism_score(cid, values | {"student_fit": sf}) for cid, sf in
              [("a", 0.2), ("b", 0.9), ("c", 0.95), ("d", 0.6), ("e", 0.6)]]
    finances = {"a": finance("a"), "b": finance("b"), "c": finance("c", "needs_aid"),
                "d": finance("d"), "e": finance("e", "no_pathway")}
    assert [s.career_id for s in rank_top_careers(scores, finances)] == ["b", "d", "a"]


def test_rank_top_careers_limit_ten() -> None:
    values = {"student_fit": 0.5, "financial_fit": 0.5, "market_demand": 0.5, "growth": 0.5, "parent_alignment": 0.5}
    scores = [prism_score(f"c{i}", values) for i in range(12)]
    ranked = rank_top_careers(scores, {s.career_id: finance(s.career_id) for s in scores})
    assert [s.career_id for s in ranked] == [f"c{i}" for i in range(10)]  # ties keep data order
