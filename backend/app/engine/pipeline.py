"""§7 pipeline: runs every stage in order and returns the results with a full PipelineTrace.

Stage 3 (System 1) runs only when no decisions are passed in; What-If and the demo cache pass the
decisions from the original run, so the rest of the pipeline is pure and fast.
"""

from datetime import date

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
from app.engine.normalize import completeness, parent_preferences, student_preferences, student_vector
from app.engine.roi import roi
from app.engine.scoring import confidence, entry_mid_inr, growth, prism_score, risk_radar
from app.engine.skills import skill_plan
from app.engine.solver import capacity, eligible_scholarships, solve_all
from app.engine.swot import swot
from app.engine.system1 import DecisionModel, run_decisions
from app.models.schemas import (
    AidScholarship,
    Career,
    CareerDetail,
    CareerFinance,
    ConflictTrace,
    Dataset,
    IngestTrace,
    MarketTrace,
    MatcherTrace,
    ParentInput,
    Pathway,
    PipelineResult,
    PipelineTrace,
    PrismScore,
    RankedCareer,
    RankingTrace,
    SchoolStudentInput,
    ScoringTrace,
    SkillPlan,
    SolverTrace,
    StudentInput,
    System1Trace,
    TypedDecision,
    VectorizeTrace,
)


def decision_probabilities(decisions: list[TypedDecision], question_id: str) -> dict[str, float]:
    """System 1 probabilities for one decision. They are used even when it abstained (§7.3)."""
    return next((d.probabilities for d in decisions if d.question_id == question_id), {})


def feasible_order(scores: dict[str, PrismScore], finances: dict[str, CareerFinance]) -> list[str]:
    """§7.9 every feasible career by score, highest first; ties keep data order."""
    feasible = [c for c in scores if finances[c].status == "feasible"]
    return sorted(feasible, key=lambda c: -scores[c].score)


def chosen_pathway(career: Career, finance: CareerFinance) -> Pathway:
    return next(p for p in career.pathways if p.id == finance.chosen_pathway_id)


def run_pipeline(
    student: StudentInput,
    parent: ParentInput,
    data: Dataset,
    as_of: date,
    model: DecisionModel | None = None,
    decisions: list[TypedDecision] | None = None,
) -> PipelineResult:
    """Run stages 1–9. Pass either a System 1 model (stage 3 runs) or earlier decisions (reused)."""
    if (model is None) == (decisions is None):
        raise ValueError("pass exactly one of model or decisions")
    careers = {c.id: c for c in data.careers}
    questions = data.questions_school if isinstance(student, SchoolStudentInput) else data.questions_college
    income = parent.annual_income_inr

    # §7.1 Stage 1: Ingest Multi-Stakeholder Inputs (already validated by the Pydantic models)
    ingest = IngestTrace(track=student.track, completeness=completeness(student, parent, questions))

    # §7.2 Stage 2: Vectorize & Normalize
    vector = student_vector(student, questions)
    s_prefs = student_preferences(student, questions)
    p_prefs = parent_preferences(parent)

    # §7.3 Stage 3: System 1 Decision Layer
    reused = decisions is not None
    if decisions is None:
        assert model is not None
        decisions = run_decisions(model, student, parent)
    affinity = decision_probabilities(decisions, config.DECISION_STUDENT_DOMAIN)
    concerns = decision_probabilities(decisions, config.DECISION_PARENT_CONCERNS)
    system1 = System1Trace(backend=decisions[0].backend if decisions else "none", reused=reused,
                           decisions=decisions, domain_affinity=affinity, parent_concerns=concerns)

    # §7.4 Stage 4: Financial Constraint Solver
    finances = {f.career_id: f for f in solve_all(data.careers, student, parent, data.scholarships)}

    # §7.5 Stage 5: Career Matcher
    fit_list = match_all(vector, data.careers, affinity, s_prefs.marks)
    fits = {f.career_id: f for f in fit_list}

    # §7.6 Stage 6: Parent-Student Conflict Index, Parent Alignment, middle path
    conflict = conflict_index(s_prefs, p_prefs, parent, affinity, student_top_career_cost(fit_list, finances))
    weights = concern_weights(concerns)
    max_entry = max(entry_mid_inr(c) for c in data.careers)
    alignments = {
        c.id: parent_alignment(c, parent, p_prefs, student.home_city, fits[c.id].student_fit,
                               finances[c.id].financial_fit, max_entry, weights)
        for c in data.careers
    }
    statuses = {c: f.status for c, f in finances.items()}
    middle = middle_path({c: f.student_fit for c, f in fits.items()},
                         {c: a.parent_alignment for c, a in alignments.items()}, statuses)

    # §7.7 Stage 7: Market Intelligence
    markets = {c.id: market_demand(c, student) for c in data.careers}

    # §7.8 Stage 8: composite score, confidence, risk
    growths = {c.id: growth(c, income) for c in data.careers}
    scores = {
        c.id: prism_score(c.id, {
            "student_fit": fits[c.id].student_fit,
            "financial_fit": finances[c.id].financial_fit,
            "market_demand": markets[c.id].market_demand,
            "growth": growths[c.id].growth,
            "parent_alignment": alignments[c.id].parent_alignment,
        })
        for c in data.careers
    }
    confidences = {c.id: confidence(ingest.completeness, decisions, c, student) for c in data.careers}
    vocabulary = {s.name: s for s in data.skills}
    plans: dict[str, SkillPlan] = {
        c.id: skill_plan(c, chosen_pathway(c, finances[c.id]), student, vector, vocabulary, as_of.year)
        for c in data.careers if finances[c.id].chosen_pathway_id is not None
    }
    risks = {c: risk_radar(careers[c], finances[c], markets[c], plans[c].mean_gap, student, income) for c in plans}

    # §7.9 Stage 9: ranking and outputs
    order = feasible_order(scores, finances)
    top_ids = order[:config.TOP_CAREERS_LIMIT]
    stretch = stretch_options(careers, finances, fits, data.scholarships, income)
    dream = dream_alternatives(student.dream_career_id, careers, finances, scores, top_ids)
    ranks = {c: i + 1 for i, c in enumerate(order)}
    ranking = [RankedCareer(rank=ranks[c], name=careers[c].name, domain=careers[c].domain, **scores[c].model_dump())
               for c in top_ids]

    detail_ids = [*top_ids, *([middle.career_id] if middle else []), *(o.career_id for o in stretch),
                  *(a.career_id for a in dream.alternatives if a.career_id in plans)] if dream else \
                 [*top_ids, *([middle.career_id] if middle else []), *(o.career_id for o in stretch)]
    exams = {e.id: e for e in data.exams}
    details: dict[str, CareerDetail] = {}
    for career_id in dict.fromkeys(detail_ids):
        career, finance = careers[career_id], finances[career_id]
        pathway = chosen_pathway(career, finance)
        aid = eligible_scholarships(pathway, career, income, data.scholarships, include_restricted=True)
        details[career_id] = CareerDetail(
            career=career, status=finance.status, rank=ranks.get(career_id), score=scores[career_id],
            student_fit=fits[career_id], finance=finance, parent_alignment=alignments[career_id],
            market=markets[career_id], growth=growths[career_id], confidence=confidences[career_id],
            risk=risks[career_id], skill_plan=plans[career_id],
            roi=roi(career, finance.effective_cost or 0), pathway=pathway,
            scholarships=[AidScholarship(scholarship_id=s.id, name=s.name, amount_inr_per_year=s.amount_inr_per_year,
                                         restricted_to=s.restricted_to)
                          for s in sorted(aid, key=lambda s: -s.amount_inr_per_year)],
            exams=[exams[e] for e in pathway.entrance_exams if e in exams],
        )

    top_swot = None
    if top_ids:
        top = top_ids[0]
        top_swot = swot(vector, plans[top].gaps, [careers[c] for c in top_ids], student,
                        {c.id: c.name for c in data.cities}, finances[top], data.scholarships, income,
                        exams, as_of.month, conflict)

    trace = PipelineTrace(
        ingest=ingest,
        vectorize=VectorizeTrace(student_vector=vector, student_preferences=s_prefs, parent_preferences=p_prefs),
        system1=system1,
        solver=SolverTrace(budget=parent.education_budget_inr, loan_factor=config.LOAN_FACTOR[parent.loan_willingness],
                           capacity=capacity(parent), solver_lambda=config.SOLVER_LAMBDA,
                           finances=list(finances.values())),
        matcher=MatcherTrace(fits=fit_list),
        conflict=ConflictTrace(conflict=conflict, concern_weights=weights,
                               parent_alignment=list(alignments.values()), middle_path=middle),
        market=MarketTrace(markets=list(markets.values())),
        scoring=ScoringTrace(growth=list(growths.values()), scores=list(scores.values()),
                             confidence=list(confidences.values()), risks=list(risks.values())),
        ranking=RankingTrace(order=order, top_career_ids=top_ids, stretch_career_ids=[o.career_id for o in stretch],
                             dream_alternative_ids=[a.career_id for a in dream.alternatives] if dream else []),
    )
    return PipelineResult(
        as_of=as_of,
        ranking=ranking,
        details=details,
        conflict=conflict,
        middle_path=middle,
        stretch_options=stretch,
        alternatives=dream,
        swot=top_swot,
        confidence=confidences[top_ids[0]] if top_ids else None,
        trace=trace,
    )
