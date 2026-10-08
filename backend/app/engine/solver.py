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
MILP_INFEASIBLE = 2


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


def _choose_with_milp(evaluations: list[PathwayEvaluation], cap: int) -> int | None:
    """Binary x_p, maximise Σ x_p·objective_p, s.t. Σ x_p = 1 and effective_cost_p·x_p ≤ capacity.

    Ties at the optimum are broken deterministically: higher quality, then lower effective cost,
    then data order, so identical input always picks the same pathway.
    """
    n = len(evaluations)
    gains = np.array([e.objective if e.objective is not None else 0.0 for e in evaluations])
    costs = np.array([float(e.effective_cost) for e in evaluations])
    result = milp(
        c=-gains,
        constraints=[
            LinearConstraint(np.ones((1, n)), lb=1, ub=1),
            LinearConstraint(np.diag(costs), lb=-np.inf, ub=cap),
        ],
        integrality=np.ones(n),
        bounds=Bounds(0, 1),
    )
    if result.status == MILP_INFEASIBLE:
        return None
    if result.status != MILP_OPTIMAL:
        raise RuntimeError(f"MILP solver failed: {result.message}")
    best = gains[int(np.argmax(result.x))]
    tied = [
        i for i, e in enumerate(evaluations)
        if e.feasible and gains[i] >= best - config.OBJECTIVE_TIE_TOLERANCE
    ]
    return min(tied, key=lambda i: (-evaluations[i].quality, evaluations[i].effective_cost, i))


def solve_career(
    career: Career, student: StudentInput, parent: ParentInput, scholarships: list[Scholarship]
) -> CareerFinance:
    budget = parent.education_budget_inr
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

    candidates = [e for e in evaluations if e.stage_fit]
    common = {"career_id": career.id, "budget": budget, "capacity": cap, "pathways": evaluations}
    if not candidates:
        return CareerFinance(status="no_pathway", chosen_pathway_id=None, effective_cost=None,
                             financial_fit=config.FF_NEEDS_AID, funding_gap=0, **common)

    index = _choose_with_milp(candidates, cap)
    if index is None:
        cheapest = min(candidates, key=lambda e: e.effective_cost)
        return CareerFinance(status="needs_aid", chosen_pathway_id=cheapest.pathway_id,
                             effective_cost=cheapest.effective_cost, financial_fit=config.FF_NEEDS_AID,
                             funding_gap=cheapest.effective_cost - cap, **common)

    chosen = candidates[index]
    return CareerFinance(status="feasible", chosen_pathway_id=chosen.pathway_id,
                         effective_cost=chosen.effective_cost,
                         financial_fit=financial_fit(chosen.effective_cost, budget, cap),
                         funding_gap=0, **common)


def solve_all(
    careers: list[Career], student: StudentInput, parent: ParentInput, scholarships: list[Scholarship]
) -> list[CareerFinance]:
    return [solve_career(c, student, parent, scholarships) for c in careers]
