"""§16 property tests: each rule must hold for 1000 random valid profiles (fixed seed)."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from hypothesis import HealthCheck, given, seed, settings
from hypothesis import strategies as st
from strategies import AS_OF, DATA, parents, profiles, stand_in_decisions, students

from app.engine import config
from app.engine.pipeline import run_pipeline
from app.engine.solver import capacity, solve_all
from app.engine.whatif import run_whatif
from app.models.schemas import PipelineResult, WhatIfOverrides

MAX_EXAMPLES = 1000
SEED = 20261008
POINTS_TOLERANCE = 0.1  # §16 component points sum to the score (±0.1)
FLOAT_TOLERANCE = 1e-9


def run(student, parent, affinity, concerns) -> PipelineResult:  # type: ignore[no-untyped-def]
    """The full pipeline with stand-in System 1 decisions built from the random probabilities."""
    return run_pipeline(student, parent, DATA, AS_OF, decisions=stand_in_decisions(affinity, concerns))


def check_feasible_within_capacity(student, parent) -> None:  # type: ignore[no-untyped-def]
    """Feasible ⇒ effective_cost ≤ capacity (for the chosen pathway and every pathway marked feasible)."""
    cap = capacity(parent)
    for finance in solve_all(DATA.careers, student, parent, DATA.scholarships):
        if finance.status == "feasible":
            assert finance.effective_cost is not None and finance.effective_cost <= cap
        for evaluation in finance.pathways:
            if evaluation.feasible:
                assert evaluation.effective_cost <= cap


def check_lower_budget_never_raises_ff(student, parent, fraction) -> None:  # type: ignore[no-untyped-def]
    """Lowering the budget never increases any career's Financial Fit."""
    lower = parent.model_copy(update={"education_budget_inr": int(parent.education_budget_inr * fraction)})
    before = solve_all(DATA.careers, student, parent, DATA.scholarships)
    after = solve_all(DATA.careers, student, lower, DATA.scholarships)
    for b, a in zip(before, after, strict=True):
        assert a.financial_fit <= b.financial_fit + FLOAT_TOLERANCE, (b.career_id, b.financial_fit, a.financial_fit)


def check_conflict_index_in_range(profile) -> None:  # type: ignore[no-untyped-def]
    """CI ∈ [0, 100]."""
    result = run(*profile)
    assert 0 <= result.conflict.index <= config.CONFLICT_INDEX_SCALE


def check_scores_in_range(profile) -> None:  # type: ignore[no-untyped-def]
    """Every PRISM score ∈ [0, 100]."""
    for score in run(*profile).trace.scoring.scores:
        assert 0 <= score.score <= sum(config.SCORE_POINTS.values())


def check_points_sum_to_score(profile) -> None:  # type: ignore[no-untyped-def]
    """Component points sum to the score (±0.1)."""
    for score in run(*profile).trace.scoring.scores:
        assert abs(sum(score.points.values()) - score.score) <= POINTS_TOLERANCE


def check_whatif_no_overrides_zero_deltas(profile) -> None:  # type: ignore[no-untyped-def]
    """What-If with no overrides gives zero deltas."""
    student, parent, affinity, concerns = profile
    result = run_whatif(student, parent, stand_in_decisions(affinity, concerns), WhatIfOverrides(), DATA, AS_OF)
    for change in result.changes:
        assert change.score_delta == 0 and change.rank_change in (0, None) and change.reason is None
        assert change.rank_before == change.rank_after
        assert all(v == 0 for v in change.point_deltas.values())


def check_deterministic(profile) -> None:  # type: ignore[no-untyped-def]
    """The pipeline is deterministic for identical input."""
    assert run(*profile).model_dump() == run(*profile).model_dump()


@dataclass(frozen=True)
class Property:
    name: str
    strategies: tuple[st.SearchStrategy[Any], ...]
    check: Callable[..., None]


PROPERTIES = [
    Property("feasible ⇒ effective_cost ≤ capacity", (students, parents()), check_feasible_within_capacity),
    Property("lowering budget never increases any FF", (students, parents(), st.floats(0.0, 1.0)),
             check_lower_budget_never_raises_ff),
    Property("CI ∈ [0, 100]", (profiles(),), check_conflict_index_in_range),
    Property("scores ∈ [0, 100]", (profiles(),), check_scores_in_range),
    Property("component points sum to the score (±0.1)", (profiles(),), check_points_sum_to_score),
    Property("What-If with no overrides gives zero deltas", (profiles(),), check_whatif_no_overrides_zero_deltas),
    Property("pipeline is deterministic for identical input", (profiles(),), check_deterministic),
]


def hypothesis_test(prop: Property, on_example: Callable[[], None] = lambda: None) -> Callable[[], None]:
    """Wrap a property in hypothesis with the fixed seed; on_example lets the benchmark count examples."""
    @seed(SEED)
    @settings(max_examples=MAX_EXAMPLES, deadline=None, database=None,
              suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large])
    @given(st.tuples(*prop.strategies))
    def test(args: tuple[Any, ...]) -> None:
        on_example()
        prop.check(*args)
    return test


test_feasible_within_capacity = hypothesis_test(PROPERTIES[0])
test_lower_budget_never_raises_ff = hypothesis_test(PROPERTIES[1])
test_conflict_index_in_range = hypothesis_test(PROPERTIES[2])
test_scores_in_range = hypothesis_test(PROPERTIES[3])
test_points_sum_to_score = hypothesis_test(PROPERTIES[4])
test_whatif_no_overrides_zero_deltas = hypothesis_test(PROPERTIES[5])
test_deterministic = hypothesis_test(PROPERTIES[6])
