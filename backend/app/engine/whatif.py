"""§11 What-If: re-run stages 2 and 4–9 with changed inputs, reusing the System 1 decisions.

Output: the new ranking, every career's rank and point deltas, and one reason sentence per career
that moved ≥ 2 ranks or ≥ 3 points, built from its largest component change. No LLM here.
"""

import time
from datetime import date

from app.engine import config
from app.engine.formatting import format_inr
from app.engine.pipeline import run_pipeline
from app.models.schemas import (
    CareerChange,
    CareerFinance,
    Dataset,
    MarketDemand,
    ParentAlignment,
    ParentInput,
    PipelineResult,
    PrismScore,
    StudentInput,
    TypedDecision,
    WhatIfOverrides,
    WhatIfResult,
)

# §11 override name → (which input, field name)
OVERRIDE_FIELDS: dict[str, tuple[str, str]] = {
    "budget": ("parent", "education_budget_inr"),
    "loan_willingness": ("parent", "loan_willingness"),
    "home_city": ("student", "home_city"),
    "willing_to_relocate": ("student", "willing_to_relocate"),
    "risk_tolerance": ("student", "risk_tolerance"),
    "risk_appetite": ("parent", "risk_appetite"),
    "wants_higher_studies": ("student", "wants_higher_studies"),
    "top_priority": ("parent", "top_priority"),
}


def apply_overrides(
    student: StudentInput, parent: ParentInput, overrides: WhatIfOverrides
) -> tuple[StudentInput, ParentInput]:
    """Copies of the inputs with the given overrides applied, validated again."""
    changes: dict[str, dict[str, object]] = {"student": {}, "parent": {}}
    for name, value in overrides.model_dump(exclude_none=True).items():
        target, field = OVERRIDE_FIELDS[name]
        changes[target][field] = value
    new_student = type(student).model_validate(student.model_dump() | changes["student"])
    new_parent = ParentInput.model_validate(parent.model_dump() | changes["parent"])
    return new_student, new_parent


class _Side:
    """One run's per-career values, looked up by career id."""

    def __init__(self, result: PipelineResult, city_names: dict[str, str]) -> None:
        trace = result.trace
        self.scores: dict[str, PrismScore] = {s.career_id: s for s in trace.scoring.scores}
        self.finances: dict[str, CareerFinance] = {f.career_id: f for f in trace.solver.finances}
        self.markets: dict[str, MarketDemand] = {m.career_id: m for m in trace.market.markets}
        self.alignments: dict[str, ParentAlignment] = {a.career_id: a for a in trace.conflict.parent_alignment}
        self.ranks = {c: i + 1 for i, c in enumerate(trace.ranking.order)}
        self.order = trace.ranking.order
        self.city_names = city_names

    def cheapest(self, career_id: str) -> int:
        return min(e.effective_cost for e in self.finances[career_id].pathways if e.stage_fit)


def _financial_cause(career_id: str, before: _Side, after: _Side, fell: bool) -> str:
    b, a = before.finances[career_id], after.finances[career_id]
    cost = format_inr(after.cheapest(career_id))
    if a.status == "needs_aid":
        return (f"even its cheapest pathway ({cost}) is now above what the family can spend "
                f"({format_inr(a.capacity)}), so it moves to stretch options with aid")
    if b.status == "needs_aid":
        return f"its cheapest pathway ({cost}) now fits within what the family can spend ({format_inr(a.capacity)})"
    if fell:
        return f"its cheapest pathway ({cost}) is now above the budget of {format_inr(a.budget)}, so it needs a loan"
    if after.cheapest(career_id) <= a.budget:
        return f"its cheapest pathway ({cost}) now fits within the budget of {format_inr(a.budget)}"
    return f"a larger loan now covers more of its cheapest pathway ({cost})"


def _market_cause(career_id: str, before: _Side, after: _Side) -> str:
    b, a = before.markets[career_id], after.markets[career_id]
    return (f"the best city it can reach is now {after.city_names[a.best_city]} with demand {a.local_demand:.2f} "
            f"(was {before.city_names[b.best_city]}, {b.local_demand:.2f})")


def _alignment_cause(career_id: str, before: _Side, after: _Side, fell: bool) -> str:
    b, a = before.alignments[career_id], after.alignments[career_id]
    part = max(a.components, key=lambda k: abs(a.weights[k] * a.components[k] - b.weights[k] * b.components[k]))
    direction = "less" if fell else "more"
    return f"it now matches {config.PA_COMPONENT_LABELS[part]} {direction} closely"


def _cause(component: str, career_id: str, before: _Side, after: _Side, fell: bool) -> str:
    if component == "financial_fit":
        return _financial_cause(career_id, before, after, fell)
    if component == "market_demand":
        return _market_cause(career_id, before, after)
    if component == "parent_alignment":
        return _alignment_cause(career_id, before, after, fell)
    return f"its {config.COMPONENT_LABELS[component]} value changed"


def reason(name: str, career_id: str, before: _Side, after: _Side) -> str:
    """§11 one sentence from the career's largest component change (by unrounded points)."""
    b, a = before.scores[career_id], after.scores[career_id]
    raw = {k: config.SCORE_POINTS[k] * (a.values[k] - b.values[k]) for k in config.SCORE_POINTS}
    component = max(raw, key=lambda k: abs(raw[k]))
    if raw[component] == 0:
        rank_b, rank_a = before.ranks.get(career_id), after.ranks.get(career_id)
        up = rank_b is not None and rank_a is not None and rank_a < rank_b
        because = "careers above it lost points" if up else "other careers gained points"
        return (f"{name} moved {'up' if up else 'down'} from #{rank_b} to #{rank_a} with its score unchanged at "
                f"{a.score:.1f}, because {because}.")
    fell = raw[component] < 0
    verb = "dropped" if a.score < b.score else "rose" if a.score > b.score else "stayed"
    scores = f"from {b.score:.1f} to {a.score:.1f}" if verb != "stayed" else f"at {a.score:.1f}"
    label = config.COMPONENT_LABELS[component]
    return (f"{name} {verb} {scores}, mainly because {label} {'fell' if fell else 'rose'} from "
            f"{b.points[component]:.1f} to {a.points[component]:.1f}: "
            f"{_cause(component, career_id, before, after, fell)}.")


def compare(base: PipelineResult, new: PipelineResult, data: Dataset) -> list[CareerChange]:
    """§11 rank and point deltas for every career, with reasons where the change is large enough."""
    city_names = {c.id: c.name for c in data.cities}
    before, after = _Side(base, city_names), _Side(new, city_names)
    names = {c.id: c.name for c in data.careers}
    ordered = list(dict.fromkeys([*after.order, *(c.id for c in data.careers)]))
    changes = []
    for career_id in ordered:
        b, a = before.scores[career_id], after.scores[career_id]
        rank_b, rank_a = before.ranks.get(career_id), after.ranks.get(career_id)
        rank_change = rank_b - rank_a if rank_b is not None and rank_a is not None else None
        score_delta = round(a.score - b.score, config.SCORE_DECIMALS)
        moved = (rank_b != rank_a) if rank_change is None else abs(rank_change) >= config.WHATIF_RANK_DELTA_THRESHOLD
        large = moved or abs(score_delta) >= config.WHATIF_POINT_DELTA_THRESHOLD
        changes.append(CareerChange(
            career_id=career_id,
            name=names[career_id],
            status_before=before.finances[career_id].status,
            status_after=after.finances[career_id].status,
            rank_before=rank_b,
            rank_after=rank_a,
            rank_change=rank_change,
            score_before=b.score,
            score_after=a.score,
            score_delta=score_delta,
            point_deltas={k: round(config.SCORE_POINTS[k] * (a.values[k] - b.values[k]), config.SCORE_DECIMALS)
                          for k in config.SCORE_POINTS},
            reason=reason(names[career_id], career_id, before, after) if large else None,
        ))
    return changes


def run_whatif(
    student: StudentInput,
    parent: ParentInput,
    decisions: list[TypedDecision],
    overrides: WhatIfOverrides,
    data: Dataset,
    as_of: date,
    assessment_id: str | None = None,
) -> WhatIfResult:
    """§11 base run and changed run with the same System 1 decisions, then the comparison."""
    start = time.perf_counter()
    base = run_pipeline(student, parent, data, as_of, decisions=decisions)
    new_student, new_parent = apply_overrides(student, parent, overrides)
    new = run_pipeline(new_student, new_parent, data, as_of, decisions=decisions)
    changes = compare(base, new, data)
    return WhatIfResult(
        assessment_id=assessment_id,
        overrides=overrides,
        ranking=new.ranking,
        changes=changes,
        elapsed_ms=(time.perf_counter() - start) * 1000,
    )
