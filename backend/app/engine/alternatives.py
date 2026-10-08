"""§10 closest routes to a dream career and §7.9 stretch options with aid ("never a dead end")."""

import numpy as np

from app.engine import config
from app.engine.solver import eligible_scholarships
from app.models.schemas import (
    AidScholarship,
    Career,
    CareerFinance,
    CheaperPathway,
    DreamAlternatives,
    PrismScore,
    RankedAlternative,
    Scholarship,
    StretchOption,
    StudentFit,
)


def dream_alternatives(
    dream_career_id: str | None,
    careers: dict[str, Career],
    finances: dict[str, CareerFinance],
    scores: dict[str, PrismScore],
    top_career_ids: list[str],
) -> DreamAlternatives | None:
    """§10 if the dream career is needs_aid or ranks outside the top 5, rank its adjacent careers."""
    if dream_career_id is None or dream_career_id not in careers:
        return None
    if finances[dream_career_id].status == "needs_aid":
        reason = "needs_aid"
    elif dream_career_id not in top_career_ids[:config.DREAM_TOP_RANK]:
        reason = "outside_top"
    else:
        return None
    adjacent = [c for c in careers[dream_career_id].adjacent_careers if c in scores]
    ranked = sorted(adjacent, key=lambda c: -scores[c].score)
    return DreamAlternatives(
        dream_career_id=dream_career_id,
        reason=reason,
        alternatives=[RankedAlternative(career_id=c, score=scores[c].score, status=finances[c].status)
                      for c in ranked],
    )


def stretch_options(
    careers: dict[str, Career],
    finances: dict[str, CareerFinance],
    fits: dict[str, StudentFit],
    scholarships: list[Scholarship],
    annual_income_inr: int,
) -> list[StretchOption]:
    """§7.9 needs_aid careers with Student Fit in the top quartile, with aid options."""
    with_pathway = [c for c in fits if finances[c].status != "no_pathway"]
    if not with_pathway:
        return []
    threshold = float(np.quantile([fits[c].student_fit for c in with_pathway], config.STRETCH_SF_QUANTILE))
    options = []
    for career_id in with_pathway:
        finance = finances[career_id]
        if finance.status != "needs_aid" or fits[career_id].student_fit < threshold:
            continue
        career = careers[career_id]
        cheapest = next(p for p in career.pathways if p.id == finance.chosen_pathway_id)
        aid = eligible_scholarships(cheapest, career, annual_income_inr, scholarships, include_restricted=True)
        stage_paths = sorted((p for p in finance.pathways if p.stage_fit), key=lambda p: p.effective_cost)
        options.append(StretchOption(
            career_id=career_id,
            student_fit=fits[career_id].student_fit,
            funding_gap=finance.funding_gap,
            cheapest_pathway_id=cheapest.id,
            scholarships=[AidScholarship(scholarship_id=s.id, name=s.name,
                                         amount_inr_per_year=s.amount_inr_per_year, restricted_to=s.restricted_to)
                          for s in sorted(aid, key=lambda s: -s.amount_inr_per_year)],
            cheaper_pathways=[CheaperPathway(pathway_id=p.pathway_id, effective_cost=p.effective_cost,
                                             funding_gap=max(0, p.effective_cost - finance.capacity))
                              for p in stage_paths],
            adjacent_feasible=[c for c in career.adjacent_careers
                               if c in finances and finances[c].status == "feasible"],
        ))
    return sorted(options, key=lambda o: -o.student_fit)
