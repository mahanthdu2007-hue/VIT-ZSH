"""§7.4 Financial Constraint Solver: scholarships, effective cost, MILP pathway choice, Financial Fit."""

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from app.engine import config
from app.models.schemas import (
    Career,
    CareerFinance,
    Entry,
    ParentInput,
    Pathway,
    PathwayEvaluation,
    SchoolStudentInput,
    Scholarship,
    StudentInput,
)

MILP_OPTIMAL = 0


def capacity(parent: ParentInput) -> int:
    """§7.4 capacity = budget × (1 + loan_factor)."""
    return round(parent.education_budget_inr * (1 + config.LOAN_FACTOR[parent.loan_willingness]))


def cost_mid(pathway: Pathway) -> int:
    """§7.4 mean of cost_inr.min and cost_inr.max (data uses whole thousands, so this is exact)."""
    return (pathway.cost_inr.min + pathway.cost_inr.max) // 2


def study_level(pathway: Pathway) -> str:
    if pathway.institution_type == config.DIPLOMA_INSTITUTION_LEVEL:
        return config.DIPLOMA_INSTITUTION_LEVEL
    return config.PATHWAY_ENTRY_STUDY_LEVEL[pathway.entry]


def eligible_scholarships(
    pathway: Pathway,
    career: Career,
    income: int,
    scholarships: list[Scholarship],
    include_restricted: bool = False,
) -> list[Scholarship]:
    """§7.4 eligible when income ≤ income_max, level matches and domain matches.

    The cost maths counts only schemes open to everyone; restricted schemes are included when
    listing aid a student may qualify for (stretch options, SWOT).
    """
    if pathway.institution_type in config.NO_SCHOLARSHIP_INSTITUTIONS:
        return []
    level = study_level(pathway)
    return [
        s for s in scholarships
        if (include_restricted or s.restricted_to is None)
        and (s.income_max_inr is None or income <= s.income_max_inr)
        and level in s.levels
        and career.domain in s.domains
    ]


def expected_scholarship(
    pathway: Pathway, career: Career, income: int, scholarships: list[Scholarship]
) -> tuple[int, str | None, bool]:
    """§7.4 best amount × duration over eligible schemes, capped at 60% of cost_mid.

    Returns (amount, scholarship id, whether the cap applied).
    """
    eligible = eligible_scholarships(pathway, career, income, scholarships)
    if not eligible:
        return 0, None, False
    best = max(eligible, key=lambda s: s.amount_inr_per_year)
    total = round(best.amount_inr_per_year * pathway.duration_years)
    cap = round(config.SCHOLARSHIP_CAP_FRACTION * cost_mid(pathway))
    return min(total, cap), best.id, total > cap


def candidate_entries(student: StudentInput) -> tuple[Entry, ...]:
    """§7.4 pathway entries that fit the student's current stage."""
    if isinstance(student, SchoolStudentInput):
        stage = "school_11_12" if student.current_class >= config.STREAM_FROM_CLASS else "school_before_11"
    else:
        stage = "college"
    return config.STAGE_ENTRIES[stage]  # type: ignore[return-value]


def objective(quality: float, effective_cost: int, cap: int) -> float | None:
    """§7.4 quality − λ·effective_cost/capacity; undefined (None) for a paid pathway at zero capacity."""
    if cap > 0:
        return quality - config.SOLVER_LAMBDA * effective_cost / cap
    return quality if effective_cost <= 0 else None


def financial_fit(cost: int, budget: int, cap: int) -> float:
    """§7.4 Financial Fit for a feasible cost (cost ≤ capacity)."""
    if cost <= budget:
        return config.FF_WITHIN_BUDGET
    if cap == budget:  # any cost above budget is needs_aid; no division
        return config.FF_NEEDS_AID
    return config.FF_WITHIN_BUDGET - config.FF_STRETCH_PENALTY * (cost - budget) / (cap - budget)


def _choose_with_milp(groups: list[list[PathwayEvaluation]], cap: int) -> list[int | None]:
    """One MILP for every career at once: binary x_p, maximise Σ x_p·objective_p, subject to
    Σ x_p = 1 within each career and effective_cost_p·x_p ≤ capacity. The objective is a sum over
    careers, so this gives each career the same choice as solving it alone, in one solver call.

    A career with no pathway within capacity is infeasible on its own (None) and is left out.
    Ties at the optimum are broken deterministically: higher quality, then lower effective cost,
    then data order, so identical input always picks the same pathway.
    """
    solvable = [g for g, group in enumerate(groups) if any(e.effective_cost <= cap for e in group)]
    choices: list[int | None] = [None] * len(groups)
    if not solvable:
        return choices
    flat = [(g, i, e) for g in solvable for i, e in enumerate(groups[g])]
    n = len(flat)
    gains = np.array([e.objective if e.objective is not None else 0.0 for _, _, e in flat])
    costs = np.array([float(e.effective_cost) for _, _, e in flat])
    one_per_career = np.array([[1.0 if fg == g else 0.0 for fg, _, _ in flat] for g in solvable])
    result = milp(
        c=-gains,
        constraints=[
            LinearConstraint(one_per_career, lb=1, ub=1),
            LinearConstraint(np.diag(costs), lb=-np.inf, ub=cap),
        ],
        integrality=np.ones(n),
        bounds=Bounds(0, 1),
        options={"mip_rel_gap": 0},
    )
    if result.status != MILP_OPTIMAL:
        raise RuntimeError(f"MILP solver failed: {result.message}")
    for g in solvable:
        rows = [k for k, (fg, _, _) in enumerate(flat) if fg == g]
        best = gains[max(rows, key=lambda k: result.x[k])]
        tied = [k for k in rows if flat[k][2].feasible and gains[k] >= best - config.OBJECTIVE_TIE_TOLERANCE]
        chosen = min(tied, key=lambda k: (-flat[k][2].quality, flat[k][2].effective_cost, flat[k][1]))
        choices[g] = flat[chosen][1]
    return choices


def evaluate_pathways(
    career: Career, student: StudentInput, parent: ParentInput, scholarships: list[Scholarship]
) -> list[PathwayEvaluation]:
    """§7.4 cost, scholarship, effective cost, feasibility and objective for every pathway."""
    cap = capacity(parent)
    entries = candidate_entries(student)
    evaluations: list[PathwayEvaluation] = []
    for pathway in career.pathways:
        stage_fit = pathway.entry in entries
        mid = cost_mid(pathway)
        amount, scholarship_id, capped = expected_scholarship(
            pathway, career, parent.annual_income_inr, scholarships
        )
        effective = mid - amount
        evaluations.append(PathwayEvaluation(
            pathway_id=pathway.id,
            label=pathway.label,
            entry=pathway.entry,
            institution_type=pathway.institution_type,
            quality=pathway.quality,
            stage_fit=stage_fit,
            cost_mid=mid,
            scholarship=amount,
            scholarship_id=scholarship_id,
            scholarship_capped=capped,
            effective_cost=effective,
            feasible=stage_fit and effective <= cap,
            objective=objective(pathway.quality, effective, cap) if stage_fit else None,
        ))
    return evaluations


def _career_finance(
    career_id: str, evaluations: list[PathwayEvaluation], index: int | None, parent: ParentInput
) -> CareerFinance:
    budget = parent.education_budget_inr
    cap = capacity(parent)
    candidates = [e for e in evaluations if e.stage_fit]
    common = {"career_id": career_id, "budget": budget, "capacity": cap, "pathways": evaluations}
    if not candidates:
        return CareerFinance(status="no_pathway", chosen_pathway_id=None, effective_cost=None,
                             financial_fit=config.FF_NEEDS_AID, funding_gap=0, **common)

    cheapest = min(candidates, key=lambda e: e.effective_cost)
    if index is None:
        return CareerFinance(status="needs_aid", chosen_pathway_id=cheapest.pathway_id,
                             effective_cost=cheapest.effective_cost, financial_fit=config.FF_NEEDS_AID,
                             funding_gap=cheapest.effective_cost - cap, **common)

    chosen = candidates[index]
    # FF uses the cheapest route the student can take, so a lower budget never raises it (§16).
    return CareerFinance(status="feasible", chosen_pathway_id=chosen.pathway_id,
                         effective_cost=chosen.effective_cost,
                         financial_fit=financial_fit(cheapest.effective_cost, budget, cap),
                         funding_gap=0, **common)


def solve_all(
    careers: list[Career], student: StudentInput, parent: ParentInput, scholarships: list[Scholarship]
) -> list[CareerFinance]:
    evaluations = [evaluate_pathways(c, student, parent, scholarships) for c in careers]
    candidates = [[e for e in group if e.stage_fit] for group in evaluations]
    choices = _choose_with_milp(candidates, capacity(parent))
    return [_career_finance(c.id, group, index, parent)
            for c, group, index in zip(careers, evaluations, choices, strict=True)]


def solve_career(
    career: Career, student: StudentInput, parent: ParentInput, scholarships: list[Scholarship]
) -> CareerFinance:
    return solve_all([career], student, parent, scholarships)[0]
