"""§11 What-If: overrides, deltas and reason sentences."""

import re

import pytest
from strategies import AS_OF, DATA, stand_in_decisions

from app.engine import config
from app.engine.whatif import OVERRIDE_FIELDS, apply_overrides, run_whatif
from app.models.schemas import WhatIfOverrides, WhatIfResult

ANANYA = next(p for p in DATA.demo_profiles if p.id == "ananya")
DECISIONS = stand_in_decisions(dict.fromkeys(config.DOMAINS, 0.05) | {"Technology": 0.9, "Engineering": 0.4}, {})


def whatif(**overrides: object) -> WhatIfResult:
    return run_whatif(ANANYA.student, ANANYA.parent, DECISIONS, WhatIfOverrides.model_validate(overrides), DATA, AS_OF)


def test_every_override_reaches_its_input_field() -> None:
    values = {"budget": 123_000, "loan_willingness": "high", "home_city": "pune", "willing_to_relocate": False,
              "risk_tolerance": "low", "risk_appetite": "high", "wants_higher_studies": False,
              "top_priority": "salary"}
    assert set(values) == set(OVERRIDE_FIELDS) == set(WhatIfOverrides.model_fields)
    student, parent = apply_overrides(ANANYA.student, ANANYA.parent, WhatIfOverrides.model_validate(values))
    for name, (target, field) in OVERRIDE_FIELDS.items():
        assert getattr(student if target == "student" else parent, field) == values[name]
    assert student.free_text_1 == ANANYA.student.free_text_1
    assert parent.annual_income_inr == ANANYA.parent.annual_income_inr


def test_no_overrides_gives_zero_deltas_and_no_reasons() -> None:
    result = whatif()
    assert len(result.changes) == len(DATA.careers)
    for change in result.changes:
        assert change.score_delta == 0 and change.reason is None
        assert change.rank_before == change.rank_after
        assert all(v == 0 for v in change.point_deltas.values())


def test_budget_cut_explains_financial_fit_drops() -> None:
    result = whatif(budget=300_000)
    by_id = {c.career_id: c for c in result.changes}
    aerospace = by_id["aerospace_engineer"]
    assert aerospace.status_before == "feasible" and aerospace.status_after == "needs_aid"
    assert aerospace.rank_after is None and aerospace.rank_change is None
    assert aerospace.reason is not None
    assert re.fullmatch(
        r"Aerospace Engineer dropped from \d+\.\d to \d+\.\d, mainly because Financial Fit fell from 20\.0 to 0\.0: "
        r"even its cheapest pathway \(₹[\d,]+\) is now above what the family can spend \(₹4,50,000\), "
        r"so it moves to stretch options with aid\.", aerospace.reason)
    assert aerospace.point_deltas["financial_fit"] == -20.0
    assert all(c.point_deltas["student_fit"] == 0 and c.point_deltas["growth"] == 0 for c in result.changes)


def test_reason_only_when_the_change_is_large_enough() -> None:
    for change in whatif(budget=300_000).changes:
        large = (abs(change.score_delta) >= config.WHATIF_POINT_DELTA_THRESHOLD
                 or (change.rank_change is not None and abs(change.rank_change) >= config.WHATIF_RANK_DELTA_THRESHOLD)
                 or (change.rank_change is None and change.rank_before != change.rank_after))
        assert (change.reason is not None) == large, change


def test_rank_change_is_positive_when_moving_up() -> None:
    for change in whatif(willing_to_relocate=False).changes:
        if change.rank_change is not None:
            assert change.rank_change == change.rank_before - change.rank_after  # type: ignore[operator]


def test_relocation_reason_names_the_city() -> None:
    reasons = [c.reason for c in whatif(willing_to_relocate=False).changes if c.reason and "Market Demand" in c.reason]
    assert reasons
    assert all("the best city it can reach is now Mysuru" in r for r in reasons)


def test_new_ranking_matches_changes() -> None:
    result = whatif(budget=300_000, top_priority="salary")
    ranked = [r.career_id for r in result.ranking]
    assert [c.career_id for c in result.changes[:len(ranked)]] == ranked
    assert [c.rank_after for c in result.changes[:len(ranked)]] == list(range(1, len(ranked) + 1))


def test_overrides_are_validated() -> None:
    with pytest.raises(ValueError):
        WhatIfOverrides.model_validate({"budget": -1})
    with pytest.raises(ValueError):
        WhatIfOverrides.model_validate({"annual_income_inr": 1})
