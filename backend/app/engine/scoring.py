"""§7.8–§7.9 Growth, PRISM score, confidence, risk radar and ranking."""

import math
from statistics import mean

from app.engine import config
from app.engine.solver import candidate_entries
from app.models.schemas import (
    Career,
    CareerFinance,
    Completeness,
    Confidence,
    Growth,
    MarketDemand,
    PrismScore,
    RiskRadar,
    StudentInput,
    TypedDecision,
)


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))


def entry_mid_inr(career: Career) -> int:
    """§7.8 entry_mid_inr = mean(entry LPA) × 1,00,000."""
    return round(mean(career.salary_inr_lpa.entry) * config.INR_PER_LPA)


def growth(career: Career, annual_income_inr: int) -> Growth:
    """§7.8 G = 0.5·growth_index + 0.3·trajectory + 0.2·mobility_uplift."""
    entry_mid = mean(career.salary_inr_lpa.entry)
    senior_mid = mean(career.salary_inr_lpa.senior)
    trajectory = _clip((senior_mid / entry_mid - 1) / config.TRAJECTORY_DIVISOR)
    mobility = _clip(math.log2(entry_mid_inr(career) / annual_income_inr) / config.MOBILITY_LOG2_DIVISOR)
    value = (config.G_WEIGHT_GROWTH_INDEX * career.growth_index
             + config.G_WEIGHT_TRAJECTORY * trajectory
             + config.G_WEIGHT_MOBILITY * mobility)
    return Growth(career_id=career.id, trajectory=trajectory, mobility_uplift=mobility, growth=value)


def prism_score(career_id: str, values: dict[str, float]) -> PrismScore:
    """§7.8 PRISM Score = 30·SF + 20·FF + 20·MD + 15·G + 15·PA, one decimal place.

    Component points are rounded to tenths by largest remainder so they add up to the score exactly.
    """
    raw = {k: config.SCORE_POINTS[k] * values[k] for k in config.SCORE_POINTS}
    scale = 10 ** config.SCORE_DECIMALS
    target = round(sum(raw.values()) * scale)
    floors = {k: math.floor(v * scale) for k, v in raw.items()}
    remainders = sorted(raw, key=lambda k: -(raw[k] * scale - floors[k]))
    for k in remainders[:target - sum(floors.values())]:
        floors[k] += 1
    return PrismScore(
        career_id=career_id,
        score=target / scale,
        values={k: values[k] for k in config.SCORE_POINTS},
        points={k: floors[k] / scale for k in config.SCORE_POINTS},
    )


def career_data_completeness(career: Career, student: StudentInput) -> float:
    """§7.8 share of the career's supporting data that is present for this student."""
    entries = candidate_entries(student)
    checks = [
        bool(career.sources),
        bool(career.skills),
        bool(career.adjacent_careers),
        any(p.entry in entries for p in career.pathways),
    ]
    return sum(checks) / len(checks)


def confidence(
    completeness: Completeness, decisions: list[TypedDecision], career: Career, student: StudentInput
) -> Confidence:
    """§7.8 Confidence = 100·(0.4·completeness + 0.35·System 1 confidence + 0.25·data completeness)."""
    answered = [d.confidence for d in decisions if not d.abstained]
    system1 = mean(answered) if answered else config.SYSTEM1_ALL_ABSTAINED_CONFIDENCE
    data = career_data_completeness(career, student)
    score = config.CONFIDENCE_SCALE * (config.CONFIDENCE_WEIGHT_COMPLETENESS * completeness.score
                                       + config.CONFIDENCE_WEIGHT_SYSTEM1 * system1
                                       + config.CONFIDENCE_WEIGHT_DATA * data)
    if score >= config.CONFIDENCE_BAND_HIGH:
        band = "High"
    elif score >= config.CONFIDENCE_BAND_MEDIUM:
        band = "Medium"
    else:
        band = "Low"
    missing = list(completeness.missing)
    for decision in decisions:
        if decision.abstained:
            missing += [f for f in config.DECISION_SOURCE_FIELDS.get(decision.question_id, ()) if f not in missing]
    return Confidence(score=score, band=band, completeness=completeness.score, system1_confidence=system1,
                      data_completeness=data, missing_inputs=missing)


def risk_radar(
    career: Career,
    finance: CareerFinance,
    market: MarketDemand,
    mean_skill_gap: float,
    student: StudentInput,
    annual_income_inr: int,
) -> RiskRadar:
    """§7.8 Risk Radar, each axis 0–1 where higher is riskier."""
    home_demand = career.city_demand[student.home_city]  # type: ignore[index]
    if home_demand < config.RISK_LOCATION_DEMAND_THRESHOLD and not student.willing_to_relocate:
        location = 1.0
    else:
        location = 1 - market.local_demand
    if finance.effective_cost is None:
        education_cost = 1.0
    else:
        education_cost = _clip(finance.effective_cost / annual_income_inr / config.RISK_EDUCATION_COST_INCOME_YEARS)
    return RiskRadar(
        career_id=career.id,
        financial=1 - finance.financial_fit,
        skill_gap=mean_skill_gap,
        market=1 - market.market_demand,
        location=location,
        education_cost=education_cost,
        disruption=career.disruption_index,
    )


def rank_top_careers(scores: list[PrismScore], finances: dict[str, CareerFinance]) -> list[PrismScore]:
    """§7.9 careers that are not needs_aid (and have a pathway), by score, top 10; ties keep data order."""
    ranked = [s for s in scores if finances[s.career_id].status == "feasible"]
    ranked.sort(key=lambda s: -s.score)
    return ranked[:config.TOP_CAREERS_LIMIT]
