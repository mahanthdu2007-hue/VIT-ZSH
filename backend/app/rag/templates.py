"""§12 deterministic explanations built only from engine values.

Used when LLM_PROVIDER=none, when the LLM call fails or returns bad JSON, and as the per-sentence
fallback for the numeric guardrail. Every number here comes from the pipeline result or the dataset.
"""

from app.engine import config
from app.engine.formatting import format_inr, points
from app.models.schemas import CareerDetail, CareerExplanation, Explanations, PipelineResult

RISK_AXES = ("financial", "skill_gap", "market", "location", "education_cost", "disruption")


def _lpa(band: tuple[float, float]) -> str:
    return f"{band[0]:g}–{band[1]:g} LPA"


def why_sentence(component: str, d: CareerDetail, city_names: dict[str, str]) -> str:
    p = points(component, d.score.points[component])
    if component == "student_fit":
        return (f"Your answers match what this career needs: Student Fit {p} "
                f"(profile match {d.student_fit.centred_cosine:.2f}, interest in {d.career.domain} "
                f"{d.student_fit.domain_affinity:.2f}).")
    if component == "financial_fit":
        cost = format_inr(d.finance.effective_cost or 0)
        if d.finance.financial_fit >= config.FF_WITHIN_BUDGET:
            return (f"It fits the family budget: Financial Fit {p}, with the {d.pathway.label} at about {cost} "
                    f"after expected scholarships (indicative estimate).")
        return (f"It is affordable with a loan: Financial Fit {p}, with the {d.pathway.label} at about {cost} "
                f"against {format_inr(d.finance.capacity)} the family can spend (indicative estimate).")
    if component == "market_demand":
        return (f"Employers are hiring: Market Demand {p}, strongest in {city_names[d.market.best_city]} "
                f"(demand {d.market.local_demand:.2f}).")
    if component == "growth":
        salary = d.career.salary_inr_lpa
        return (f"It has room to grow: Growth {p}, with pay rising from about {_lpa(salary.entry)} at entry to "
                f"{_lpa(salary.senior)} at senior level (indicative estimate).")
    return f"It matches what your family hopes for: Parent Alignment {p}."


def why_not_sentence(axis: str, d: CareerDetail, city_names: dict[str, str], home_city: str,
                     income: int) -> str:
    risk = d.risk
    if axis == "financial":
        return (f"Paying for it is a stretch: Financial Fit {points('financial_fit', d.score.points['financial_fit'])} "
                f"against a budget of {format_inr(d.finance.budget)}.")
    if axis == "skill_gap":
        gap = d.skill_plan.gaps[0]
        return (f"There are skills to build first: the biggest gap is {gap.skill} "
                f"({gap.current:.0%} now, {gap.level_required:.0%} needed).")
    if axis == "market":
        return (f"Jobs are not guaranteed: Market Demand is {points('market_demand', d.score.points['market_demand'])}, "
                f"with hiring strongest in {city_names[d.market.best_city]}.")
    if axis == "location":
        return (f"Jobs near home are fewer: demand in {city_names[home_city]} is "
                f"{d.career.city_demand[home_city]:.2f}.")  # type: ignore[index]
    if axis == "education_cost":
        years = (d.finance.effective_cost or 0) / income
        return (f"The course costs about {format_inr(d.finance.effective_cost or 0)}, which is {years:.1f} years "
                f"of family income (indicative estimate).")
    return (f"Automation may change this work: its Economic Disruption Index is "
            f"{risk.disruption:.2f}.")


def roadmap_narrative(d: CareerDetail) -> str:
    gaps = [g.skill for g in d.skill_plan.gaps if g.gap > 0][:2]
    learn = f" Along the way, build {' and '.join(gaps)}." if gaps else ""
    return (f"Suggested route: {d.pathway.label}, about {d.pathway.duration_years:g} years and around "
            f"{format_inr(d.finance.effective_cost or 0)} after expected scholarships (indicative estimate). "
            f"Steps: {' → '.join(d.pathway.steps)}.{learn} It pays back in about {d.roi.break_even_years:.1f} "
            f"years if {d.roi.salary_share:.0%} of the entry salary goes to the cost.")


def explain_career(d: CareerDetail, city_names: dict[str, str], home_city: str, income: int) -> CareerExplanation:
    by_value = sorted(config.SCORE_POINTS, key=lambda k: -d.score.values[k])
    risk_values = d.risk.model_dump()
    by_risk = sorted(RISK_AXES, key=lambda a: -risk_values[a])
    chosen = next(e for e in d.finance.pathways if e.pathway_id == d.pathway.id)
    cited = [d.career.id, d.pathway.id, *([chosen.scholarship_id] if chosen.scholarship_id else []),
             *(e.id for e in d.exams)]
    return CareerExplanation(
        career_id=d.career.id,
        why=[why_sentence(k, d, city_names) for k in by_value[:config.EXPLAIN_WHY_COUNT]],
        why_not=[why_not_sentence(a, d, city_names, home_city, income)
                 for a in by_risk[:config.EXPLAIN_WHY_NOT_COUNT]],
        roadmap_narrative=roadmap_narrative(d),
        cited_ids=cited,
    )


def explained_ids(result: PipelineResult) -> list[str]:
    """§12 the top 5 careers, then the middle path if it is not among them."""
    ids = [r.career_id for r in result.ranking[:config.EXPLAIN_TOP_N]]
    if result.middle_path and result.middle_path.career_id not in ids:
        ids.append(result.middle_path.career_id)
    return ids


def template_explanations(result: PipelineResult, city_names: dict[str, str], home_city: str,
                          income: int) -> Explanations:
    return Explanations(
        source="template",
        items=[explain_career(result.details[c], city_names, home_city, income) for c in explained_ids(result)],
    )
