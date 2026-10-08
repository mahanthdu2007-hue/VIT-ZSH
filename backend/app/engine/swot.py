"""§9 SWOT: deterministic, structured items built from engine values."""

from app.engine import config
from app.engine.market import reachable_cities
from app.engine.solver import eligible_scholarships
from app.models.schemas import (
    Career,
    CareerFinance,
    ConflictResult,
    Exam,
    Scholarship,
    SkillGap,
    StudentInput,
    StudentVector,
    Swot,
    SwotItem,
)


def strengths(vector: StudentVector) -> list[SwotItem]:
    """S: the student's top 3 dimensions with values."""
    order = list(config.STUDENT_DIMENSIONS)
    top = sorted(order, key=lambda d: (-vector.values[d], order.index(d)))
    return [SwotItem(kind="dimension", label=d, value=vector.values[d])
            for d in top[:config.SWOT_ITEMS_PER_QUADRANT]]


def weaknesses(gaps: list[SkillGap]) -> list[SwotItem]:
    """W: the top 3 skill gaps for the #1 career."""
    return [SwotItem(kind="skill_gap", label=g.skill, value=g.gap)
            for g in gaps if g.gap > 0][:config.SWOT_ITEMS_PER_QUADRANT]


def months_until(month: str, current_month: int) -> int:
    return (config.MONTHS.index(month) - (current_month - 1)) % len(config.MONTHS)


def opportunities(
    top_careers: list[Career],
    student: StudentInput,
    city_names: dict[str, str],
    top_career: Career,
    top_finance: CareerFinance,
    scholarships: list[Scholarship],
    annual_income_inr: int,
    exams: dict[str, Exam],
    current_month: int,
) -> list[SwotItem]:
    """O: top 3 high-demand opportunities in reachable cities, eligible scholarships, next exams."""
    n = config.SWOT_ITEMS_PER_QUADRANT
    cities = reachable_cities(student)
    pairs = [(rank, career, city) for rank, career in enumerate(top_careers) for city in cities]
    pairs.sort(key=lambda t: (-t[1].city_demand[t[2]], t[0], cities.index(t[2])))
    items = [SwotItem(kind="city_demand", label=f"{career.name} in {city_names[city]}",
                      value=career.city_demand[city]) for _, career, city in pairs[:n]]

    pathway = next(p for p in top_career.pathways if p.id == top_finance.chosen_pathway_id)
    aid = eligible_scholarships(pathway, top_career, annual_income_inr, scholarships, include_restricted=True)
    aid.sort(key=lambda s: -s.amount_inr_per_year)
    items += [SwotItem(kind="scholarship", label=s.name, value=s.amount_inr_per_year) for s in aid[:n]]

    upcoming = [exams[e] for e in pathway.entrance_exams if e in exams]
    upcoming.sort(key=lambda e: months_until(e.typical_month, current_month))
    items += [SwotItem(kind="exam", label=f"{e.name} ({e.typical_month})",
                       value=months_until(e.typical_month, current_month)) for e in upcoming[:n]]
    return items


def threats(top_career: Career, top_finance: CareerFinance, conflict: ConflictResult) -> list[SwotItem]:
    """T: disruption index of the top career, funding gap if any, top conflict hotspot."""
    items = [SwotItem(kind="disruption", label=top_career.name, value=top_career.disruption_index)]
    if top_finance.funding_gap > 0:
        items.append(SwotItem(kind="funding_gap", label=top_career.name, value=top_finance.funding_gap))
    if conflict.hotspots:
        hotspot = next(d for d in conflict.dimensions if d.name == conflict.hotspots[0])
        items.append(SwotItem(kind="conflict", label=hotspot.name, value=hotspot.points))
    return items


def swot(
    vector: StudentVector,
    gaps: list[SkillGap],
    top_careers: list[Career],
    student: StudentInput,
    city_names: dict[str, str],
    top_finance: CareerFinance,
    scholarships: list[Scholarship],
    annual_income_inr: int,
    exams: dict[str, Exam],
    current_month: int,
    conflict: ConflictResult,
) -> Swot:
    top_career = top_careers[0]
    return Swot(
        strengths=strengths(vector),
        weaknesses=weaknesses(gaps),
        opportunities=opportunities(top_careers, student, city_names, top_career, top_finance,
                                    scholarships, annual_income_inr, exams, current_month),
        threats=threats(top_career, top_finance, conflict),
    )
