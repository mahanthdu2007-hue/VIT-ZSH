"""Runs engine stages 2 and 4–9 in order for the property tests and the benchmark.

pipeline.py and whatif.py are later phases, so this chains the existing engine modules the same
way. System 1 (§7.3) is not built yet, so domain affinity and parent concerns are inputs here.
"""

from dataclasses import dataclass
from typing import Any

from app.engine import config
from app.engine.alternatives import dream_alternatives, stretch_options
from app.engine.conflict import (
    concern_weights,
    conflict_index,
    middle_path,
    parent_alignment,
    student_top_career_cost,
)
from app.engine.market import market_demand
from app.engine.matcher import match_all
from app.engine.normalize import parent_preferences, student_preferences, student_vector
from app.engine.roi import roi
from app.engine.scoring import entry_mid_inr, growth, prism_score, rank_top_careers, risk_radar
from app.engine.skills import skill_plan
from app.engine.solver import solve_all
from app.engine.swot import swot
from app.models.schemas import (
    CareerFinance,
    ConflictResult,
    Dataset,
    DreamAlternatives,
    MiddlePath,
    ParentInput,
    PrismScore,
    RiskRadar,
    Roi,
    SchoolStudentInput,
    SkillPlan,
    StretchOption,
    StudentFit,
    StudentInput,
    Swot,
)

CURRENT_YEAR = 2026
CURRENT_MONTH = 10

# §11 What-If override name → (which input, field name)
WHATIF_FIELDS: dict[str, tuple[str, str]] = {
    "budget": ("parent", "education_budget_inr"),
    "loan_willingness": ("parent", "loan_willingness"),
    "home_city": ("student", "home_city"),
    "willing_to_relocate": ("student", "willing_to_relocate"),
    "risk_tolerance": ("student", "risk_tolerance"),
    "risk_appetite": ("parent", "risk_appetite"),
    "wants_higher_studies": ("student", "wants_higher_studies"),
    "top_priority": ("parent", "top_priority"),
}


@dataclass
class ChainResult:
    finances: dict[str, CareerFinance]
    fits: dict[str, StudentFit]
    conflict: ConflictResult
    scores: dict[str, PrismScore]
    ranking: list[PrismScore]
    risks: dict[str, RiskRadar]
    middle_path: MiddlePath | None
    stretch: list[StretchOption]
    dream: DreamAlternatives | None
    top_plan: SkillPlan | None
    top_swot: Swot | None
    top_roi: Roi | None

    def dump(self) -> Any:
        """Plain data for comparing two runs."""
        def plain(value: Any) -> Any:
            if hasattr(value, "model_dump"):
                return value.model_dump()
            if isinstance(value, dict):
                return {k: plain(v) for k, v in value.items()}
            if isinstance(value, list):
                return [plain(v) for v in value]
            return value
        return {k: plain(v) for k, v in vars(self).items()}


def run(
    student: StudentInput,
    parent: ParentInput,
    domain_affinity: dict[str, float],
    concerns: dict[str, float],
    data: Dataset,
) -> ChainResult:
    questions = data.questions_school if isinstance(student, SchoolStudentInput) else data.questions_college
    careers = {c.id: c for c in data.careers}
    vector = student_vector(student, questions)
    s_prefs = student_preferences(student, questions)
    p_prefs = parent_preferences(parent)
    income = parent.annual_income_inr

    finances = {f.career_id: f for f in solve_all(data.careers, student, parent, data.scholarships)}
    fit_list = match_all(vector, data.careers, domain_affinity, s_prefs.marks)
    fits = {f.career_id: f for f in fit_list}
    conflict = conflict_index(s_prefs, p_prefs, parent, domain_affinity,
                              student_top_career_cost(fit_list, finances))
    weights = concern_weights(concerns)
    max_entry = max(entry_mid_inr(c) for c in data.careers)

    scores: dict[str, PrismScore] = {}
    alignments: dict[str, float] = {}
    risks: dict[str, RiskRadar] = {}
    vocabulary = {s.name: s for s in data.skills}
    for career in data.careers:
        finance, fit = finances[career.id], fits[career.id].student_fit
        alignments[career.id] = parent_alignment(career, parent, p_prefs, student.home_city, fit,
                                                 finance.financial_fit, max_entry, weights).parent_alignment
        market = market_demand(career, student)
        scores[career.id] = prism_score(career.id, {
            "student_fit": fit,
            "financial_fit": finance.financial_fit,
            "market_demand": market.market_demand,
            "growth": growth(career, income).growth,
            "parent_alignment": alignments[career.id],
        })
        if finance.chosen_pathway_id is not None:
            pathway = next(p for p in career.pathways if p.id == finance.chosen_pathway_id)
            plan = skill_plan(career, pathway, student, vector, vocabulary, CURRENT_YEAR)
            risks[career.id] = risk_radar(career, finance, market, plan.mean_gap, student, income)

    ranking = rank_top_careers(list(scores.values()), finances)
    statuses = {c: f.status for c, f in finances.items()}
    top_ids = [s.career_id for s in ranking]

    top_plan = top_swot = top_roi = None
    if ranking:
        top = careers[top_ids[0]]
        top_finance = finances[top.id]
        pathway = next(p for p in top.pathways if p.id == top_finance.chosen_pathway_id)
        top_plan = skill_plan(top, pathway, student, vector, vocabulary, CURRENT_YEAR)
        top_swot = swot(vector, top_plan.gaps, [careers[c] for c in top_ids], student,
                        {c.id: c.name for c in data.cities}, top_finance, data.scholarships, income,
                        {e.id: e for e in data.exams}, CURRENT_MONTH, conflict)
        top_roi = roi(top, top_finance.effective_cost or 0)

    return ChainResult(
        finances=finances,
        fits=fits,
        conflict=conflict,
        scores=scores,
        ranking=ranking,
        risks=risks,
        middle_path=middle_path({c: f.student_fit for c, f in fits.items()}, alignments, statuses),
        stretch=stretch_options(careers, finances, fits, data.scholarships, income),
        dream=dream_alternatives(student.dream_career_id, careers, finances, scores, top_ids),
        top_plan=top_plan,
        top_swot=top_swot,
        top_roi=top_roi,
    )


def apply_overrides(
    student: StudentInput, parent: ParentInput, overrides: dict[str, Any]
) -> tuple[StudentInput, ParentInput]:
    """§11 apply What-If overrides to copies of the inputs (validated again)."""
    changes: dict[str, dict[str, Any]] = {"student": {}, "parent": {}}
    for name, value in overrides.items():
        target, field = WHATIF_FIELDS[name]
        changes[target][field] = value
    new_student = type(student).model_validate(student.model_dump() | changes["student"])
    new_parent = ParentInput.model_validate(parent.model_dump() | changes["parent"])
    return new_student, new_parent


def deltas(base: ChainResult, new: ChainResult) -> dict[str, dict[str, float]]:
    """§11 per-career rank delta and per-component point deltas (rank 0 = not in the top list)."""
    def ranks(result: ChainResult) -> dict[str, int]:
        return {s.career_id: i + 1 for i, s in enumerate(result.ranking)}
    base_ranks, new_ranks = ranks(base), ranks(new)
    out: dict[str, dict[str, float]] = {}
    for career_id, score in base.scores.items():
        after = new.scores[career_id]
        out[career_id] = {"rank": new_ranks.get(career_id, 0) - base_ranks.get(career_id, 0),
                          "score": after.score - score.score}
        out[career_id] |= {k: after.points[k] - score.points[k] for k in config.SCORE_POINTS}
    return out
