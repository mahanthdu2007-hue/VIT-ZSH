"""§7.6 Parent-Student Conflict Index, per-career Parent Alignment and the Nash middle path."""

from statistics import median

from app.engine import config
from app.engine.scoring import entry_mid_inr
from app.models.schemas import (
    Career,
    CareerFinance,
    CareerStatus,
    ConflictDimension,
    ConflictResult,
    MiddlePath,
    NashCandidate,
    ParentAlignment,
    ParentInput,
    ParentPreferences,
    StudentFit,
    StudentPreferences,
)


def student_top_domains(domain_affinity: dict[str, float]) -> list[str]:
    """§7.6 the student's top-3 affinity domains (ties broken by the §5 domain order)."""
    order = {d: i for i, d in enumerate(config.DOMAINS)}
    positive = [d for d, v in domain_affinity.items() if v > 0]
    positive.sort(key=lambda d: (-domain_affinity[d], order.get(d, len(order))))
    return positive[:config.CONFLICT_STUDENT_TOP_DOMAINS]


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 1.0


def student_top_career_cost(fits: list[StudentFit], finances: dict[str, CareerFinance]) -> int | None:
    """Effective cost of the student's own top career (highest Student Fit with any pathway)."""
    usable = [f for f in fits if finances[f.career_id].status != "no_pathway"]
    if not usable:
        return None
    top = max(usable, key=lambda f: f.student_fit)
    return finances[top.career_id].effective_cost


def _cost_mismatch(cost: int | None, budget: int) -> float:
    if cost is None:
        return 0.0
    if budget == 0:
        return 1.0 if cost > 0 else 0.0
    return min(1.0, max(0.0, (cost - budget) / budget))


def conflict_index(
    student: StudentPreferences,
    parent_prefs: ParentPreferences,
    parent: ParentInput,
    domain_affinity: dict[str, float],
    top_career_cost: int | None,
) -> ConflictResult:
    """§7.6 CI = 100 · Σ weight · mismatch, with the per-dimension breakdown and top 2 hotspots."""
    top_domains = student_top_domains(domain_affinity)
    if top_domains and parent.preferred_domains:
        domain_mismatch = 1 - jaccard(set(top_domains), set(parent.preferred_domains))
    else:  # no stated preference on one side means no domain conflict
        domain_mismatch = 0.0

    raw: dict[str, tuple[float | None, float | None, float]] = {
        "domain": (None, None, domain_mismatch),
        "risk": (student.risk_tolerance, parent_prefs.risk_appetite,
                 abs(student.risk_tolerance - parent_prefs.risk_appetite)),
        "location": (student.relocation, parent_prefs.location,
                     abs(student.relocation - parent_prefs.location)),
        "higher_studies": (student.higher_studies, parent_prefs.higher_studies,
                           abs(student.higher_studies - parent_prefs.higher_studies)),
        "cost": (None, None, _cost_mismatch(top_career_cost, parent.education_budget_inr)),
        "stability_vs_passion": (student.stability, parent_prefs.priority_stability,
                                 abs(student.stability - parent_prefs.priority_stability)),
    }
    dimensions = [
        ConflictDimension(
            name=name, weight=weight, student_value=raw[name][0], parent_value=raw[name][1],
            mismatch=raw[name][2], points=config.CONFLICT_INDEX_SCALE * weight * raw[name][2],
        )
        for name, weight in config.CONFLICT_WEIGHTS.items()
    ]
    ranked = sorted((d for d in dimensions if d.points > 0), key=lambda d: -d.points)
    return ConflictResult(
        index=sum(d.points for d in dimensions),
        dimensions=dimensions,
        hotspots=[d.name for d in ranked[:config.CONFLICT_TOP_HOTSPOTS]],
        student_top_domains=top_domains,
    )


def concern_weights(concerns: dict[str, float]) -> dict[str, float]:
    """§7.6 each concern with probability > 0.5 adds +0.1 to its dimension; then renormalise."""
    weights = dict(config.PA_WEIGHTS)
    for concern, probability in concerns.items():
        dimension = config.PARENT_CONCERN_DIMENSION.get(concern)
        if dimension is not None and probability > config.PARENT_CONCERN_THRESHOLD:
            weights[dimension] += config.PARENT_CONCERN_BOOST
    total = sum(weights.values())
    return {k: v / total for k, v in weights.items()}


def parent_alignment(
    career: Career,
    parent: ParentInput,
    parent_prefs: ParentPreferences,
    home_city: str,
    student_fit: float,
    financial_fit: float,
    max_entry_salary_inr: int,
    weights: dict[str, float],
) -> ParentAlignment:
    """§7.6 per-career PA: weighted mean of domain, risk, location, priority fit and FF."""
    if parent.preferred_domains:
        domain = config.PA_DOMAIN_MATCH if career.domain in parent.preferred_domains else config.PA_DOMAIN_MISMATCH
    else:
        domain = config.PA_DOMAIN_MATCH
    location = career.city_demand[home_city] if parent.location_preference == "near_home" else 1.0  # type: ignore[index]
    priority_values = {
        "stability": career.stability,
        "entry_salary": entry_mid_inr(career) / max_entry_salary_inr,
        "prestige": career.prestige,
        "student_fit": student_fit,
    }
    components = {
        "domain": domain,
        "risk": 1 - abs(career.risk_level - parent_prefs.risk_appetite),
        "location": location,
        "priority": priority_values[config.PA_PRIORITY_SOURCE[parent.top_priority]],
        "financial_fit": financial_fit,
    }
    value = sum(weights[k] * components[k] for k in components) / sum(weights.values())
    return ParentAlignment(career_id=career.id, components=components, weights=weights, parent_alignment=value)


def middle_path(
    student_utility: dict[str, float],
    parent_utility: dict[str, float],
    statuses: dict[str, CareerStatus],
) -> MiddlePath | None:
    """§7.6 Nash bargaining: argmax (U_s − d_s)(U_p − d_p) over feasible careers with both terms > 0.

    d = (median U_s, median U_p) over careers that are not needs_aid (and have a pathway).
    Falls back to the career with the highest min(U_s, U_p) when no career qualifies.
    """
    feasible = [c for c in student_utility if statuses[c] == "feasible"]
    if not feasible:
        return None
    d_s = median(student_utility[c] for c in feasible)
    d_p = median(parent_utility[c] for c in feasible)
    order = {c: i for i, c in enumerate(feasible)}

    candidates = [
        NashCandidate(career_id=c, u_s=student_utility[c], u_p=parent_utility[c],
                      product=(student_utility[c] - d_s) * (parent_utility[c] - d_p))
        for c in feasible
        if student_utility[c] > d_s and parent_utility[c] > d_p
    ]
    candidates.sort(key=lambda n: (-n.product, order[n.career_id]))
    if candidates:
        chosen, method = candidates[0].career_id, "nash"
    else:
        chosen = max(feasible, key=lambda c: (min(student_utility[c], parent_utility[c]), -order[c]))
        method = "max_min"

    student_top = max(feasible, key=lambda c: (student_utility[c], -order[c]))
    parent_top = max(feasible, key=lambda c: (parent_utility[c], -order[c]))
    return MiddlePath(
        career_id=chosen,
        method=method,
        disagreement_s=d_s,
        disagreement_p=d_p,
        u_s=student_utility[chosen],
        u_p=parent_utility[chosen],
        student_top_career_id=student_top,
        student_change=student_utility[chosen] - student_utility[student_top],
        parent_top_career_id=parent_top,
        parent_change=parent_utility[chosen] - parent_utility[parent_top],
        student_gain=student_utility[chosen] - d_s,
        parent_gain=parent_utility[chosen] - d_p,
        candidates=candidates[:config.NASH_CANDIDATES_SHOWN],
    )
