"""§12 System 2 explanations: the LLM rewords already-computed results, and the guardrail checks every number.

For the top 5 careers + middle path: retrieve CONTEXT (filtered to those careers), send it with ENGINE_RESULT
in one request, ask for JSON at temperature 0.2, then run the numeric guardrail sentence by sentence. Any career
whose item is missing or unusable, or every career if the call fails, gets its template explanation instead.
"""

import json
import time
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.engine import config
from app.engine.formatting import format_inr
from app.models.schemas import (
    CareerDetail,
    CareerExplainTrace,
    CareerExplanation,
    Explanations,
    GuardrailHit,
    ParentInput,
    PipelineResult,
    StudentInput,
    System2Trace,
)
from app.rag import guardrail
from app.rag.index import IndexDoc, citation, retrieve
from app.rag.llm import LLMError, Provider
from app.rag.templates import detail_doc_ids, explain_career, explained_ids

SYSTEM_PROMPT = f"""You explain career results to an Indian school or college student and their parents.
ENGINE_RESULT lists several careers. Return {{"items": [...]}} with one object per career, in the same order.
Each object explains only its own career, using that career's ENGINE_RESULT entry and CONTEXT documents.
Rules:
- Use only facts in CONTEXT and ENGINE_RESULT. Every number you write must be copied exactly from them.
  Never calculate, estimate, convert or round a number yourself.
- The engine already decided the scores and ranking; explain them, do not judge them.
- Plain, warm language a Class 9 student understands; speak to the student as "you".
- Money values are indicative estimates. Never promise admission, salaries or outcomes.
- why: exactly {config.EXPLAIN_WHY_COUNT} short sentences on why this career fits.
- why_not: exactly {config.EXPLAIN_WHY_NOT_COUNT} short sentences on what to watch out for.
- roadmap_narrative: 2 to 4 sentences describing the suggested route step by step.
- cited_ids: the ids in square brackets of the CONTEXT documents you used."""


class LLMExplanation(BaseModel):
    """§12 the JSON the LLM must return for one career."""
    career_id: str
    why: list[str]
    why_not: list[str]
    roadmap_narrative: str
    cited_ids: list[str]


class LLMExplanationSet(BaseModel):
    """All careers in one request (the Gemini free tier allows 20 requests a day); items are checked one by one."""
    items: list[dict[str, Any]] = Field(json_schema_extra={"items": LLMExplanation.model_json_schema()})


def engine_result(d: CareerDetail, result: PipelineResult, city_names: dict[str, str], student: StudentInput,
                  parent: ParentInput) -> dict[str, Any]:
    """ENGINE_RESULT: the computed values for one career, the only numbers the LLM may quote."""
    chosen = next(e for e in d.finance.pathways if e.pathway_id == d.pathway.id)
    salary = d.career.salary_inr_lpa
    return {
        "career_id": d.career.id, "career": d.career.name, "domain": d.career.domain,
        "rank": d.rank, "status": d.status, "prism_score": d.score.score,
        "points": {config.COMPONENT_LABELS[k]: {"earned": round(v, 1), "out_of": config.SCORE_POINTS[k]}
                   for k, v in d.score.points.items()},
        "is_middle_path": result.middle_path is not None and result.middle_path.career_id == d.career.id,
        "suggested_route": {"label": d.pathway.label, "steps": d.pathway.steps,
                            "duration_years": d.pathway.duration_years},
        "cost_indicative": {"course_cost": format_inr(chosen.cost_mid),
                            "expected_scholarship": format_inr(chosen.scholarship),
                            "cost_after_scholarship": format_inr(d.finance.effective_cost or 0),
                            "family_budget": format_inr(d.finance.budget),
                            "budget_with_loan": format_inr(d.finance.capacity),
                            "funding_gap": format_inr(d.finance.funding_gap)},
        "salary_indicative": {"entry": f"{salary.entry[0]:g}–{salary.entry[1]:g} LPA",
                              "mid": f"{salary.mid[0]:g}–{salary.mid[1]:g} LPA",
                              "senior": f"{salary.senior[0]:g}–{salary.senior[1]:g} LPA"},
        "student_fit": {"profile_match": round(d.student_fit.centred_cosine, 2),
                        "interest_in_domain": round(d.student_fit.domain_affinity, 2)},
        "market": {"best_city": city_names[d.market.best_city], "local_demand": round(d.market.local_demand, 2),
                   "home_city": city_names[student.home_city],
                   "home_city_demand": d.career.city_demand[student.home_city]},
        "economic_disruption_index": d.career.disruption_index,
        "risk_radar": {k: round(v, 2) for k, v in d.risk.model_dump().items() if k != "career_id"},
        "top_skill_gaps": [{"skill": g.skill, "now_percent": round(g.current * 100),
                            "needed_percent": round(g.level_required * 100)}
                           for g in d.skill_plan.gaps if g.gap > 0][:3],
        "timeline": [{"year": t.year, "steps": t.steps} for t in d.skill_plan.timeline],
        "payback_years": round(d.roi.break_even_years, 1),
        "payback_assumes_salary_share_percent": round(d.roi.salary_share * 100),
        "entrance_exams": [{"name": e.name, "usually_in": e.typical_month} for e in d.exams],
        "scholarships": [s.name for s in d.scholarships],
        "family_income": format_inr(parent.annual_income_inr),
        "cost_in_years_of_family_income": round((d.finance.effective_cost or 0) / parent.annual_income_inr, 1),
    }


def _context_text(docs: list[IndexDoc]) -> str:
    return "\n".join(f"[{d.doc_id}] {d.text}" for d in docs)


def _sentences_checked(career_id: str, field: str, llm_items: list[str], template_items: list[str], count: int,
                       allowed: set[float], hits: list[GuardrailHit]) -> list[str]:
    """Exactly `count` sentences: the LLM's where every number is supported, else the template's (§12)."""
    out: list[str] = []
    for i in range(count):
        template = template_items[i] if i < len(template_items) else None
        sentence = llm_items[i].strip() if i < len(llm_items) else ""
        bad = guardrail.unsupported_numbers(sentence, allowed) if sentence else []
        if sentence and not bad:
            out.append(sentence)
            continue
        if sentence:
            hits.append(GuardrailHit(career_id=career_id, field=f"{field}[{i}]", sentence=sentence, unsupported=bad,
                                     action="replaced" if template else "removed", replacement=template))
        if template:
            out.append(template)
    return out


def _narrative_checked(career_id: str, narrative: str, template: str, allowed: set[float],
                       hits: list[GuardrailHit]) -> str:
    """Drop each narrative sentence with an unsupported number; the template narrative if none survive."""
    kept: list[str] = []
    for sentence in guardrail.split_sentences(narrative):
        bad = guardrail.unsupported_numbers(sentence, allowed)
        if bad:
            hits.append(GuardrailHit(career_id=career_id, field="roadmap_narrative", sentence=sentence,
                                     unsupported=bad, action="removed", replacement=None))
        else:
            kept.append(sentence)
    return " ".join(kept) if kept else template


def apply_guardrail(llm: LLMExplanation, template: CareerExplanation, engine: dict[str, Any], docs: list[IndexDoc],
                    hits: list[GuardrailHit]) -> CareerExplanation:
    """§12 numeric guardrail plus citation clean-up on one LLM explanation."""
    allowed = guardrail.allowed_values(engine, [d.text for d in docs])
    career_id = template.career_id
    known = {d.doc_id: d for d in docs} | {d.id: d for d in docs if d.career_id in ("", career_id)}
    cited = list(dict.fromkeys(known[c].doc_id for c in llm.cited_ids if c in known))
    citations = [citation(c) for c in cited] or template.citations
    return CareerExplanation(
        career_id=career_id,
        why=_sentences_checked(career_id, "why", llm.why, template.why, config.EXPLAIN_WHY_COUNT, allowed, hits),
        why_not=_sentences_checked(career_id, "why_not", llm.why_not, template.why_not,
                                   config.EXPLAIN_WHY_NOT_COUNT, allowed, hits),
        roadmap_narrative=_narrative_checked(career_id, llm.roadmap_narrative, template.roadmap_narrative,
                                             allowed, hits),
        cited_ids=[c.id for c in citations],
        citations=citations,
        source="llm",
    )


def _llm_items(raw: dict[str, Any]) -> dict[str, LLMExplanation]:
    """Each well-formed item by career id; a malformed item only costs that one career its LLM text."""
    items: dict[str, LLMExplanation] = {}
    for value in raw["items"]:
        try:
            item = LLMExplanation.model_validate(value)
        except ValidationError:
            continue
        items.setdefault(item.career_id, item)
    return items


def llm_explanations(provider: Provider, result: PipelineResult, templates: Explanations,
                     city_names: dict[str, str], student: StudentInput, parent: ParentInput) -> Explanations:
    """§12 LLM explanations for the top 5 careers + middle path in one request, with per-career template
    fallback and the numeric guardrail checked against each career's own ENGINE_RESULT and CONTEXT."""
    started = time.perf_counter()
    ids = explained_ids(result)
    linked = list(dict.fromkeys(doc_id for c in ids for doc_id in detail_doc_ids(result.details[c])
                                if not doc_id.startswith(("career:", "pathway:"))))
    docs, retrieval = retrieve(ids, linked)
    engines = {c: engine_result(result.details[c], result, city_names, student, parent) for c in ids}
    own_docs = {c: [d for d in docs if d.career_id == c or d.doc_id in detail_doc_ids(result.details[c])]
                for c in ids}
    user = (f"ENGINE_RESULT:\n{json.dumps(list(engines.values()), ensure_ascii=False)}\n\n"
            f"CONTEXT:\n{_context_text(docs)}\n\nExplain these careers, in this order: {', '.join(ids)}.")

    reason: str | None = None
    llm_items: dict[str, LLMExplanation] = {}
    try:
        llm_items = _llm_items(provider.complete_json(SYSTEM_PROMPT, user, LLMExplanationSet,
                                                      timeout_s=config.EXPLAIN_TIMEOUT_S))
    except LLMError as error:
        reason = f"{type(error).__name__}: {error}"[:200]
    duration_ms = round((time.perf_counter() - started) * 1000)

    items: list[CareerExplanation] = []
    careers: list[CareerExplainTrace] = []
    hits: list[GuardrailHit] = []
    for template in templates.items:
        career_id = template.career_id
        llm_item = llm_items.get(career_id)
        item = template if llm_item is None else apply_guardrail(llm_item, template, engines[career_id],
                                                                  own_docs[career_id], hits)
        items.append(item)
        careers.append(CareerExplainTrace(
            career_id=career_id, source=item.source,
            fallback_reason=None if llm_item else reason or "LLMBadResponse: no valid item for this career",
            retrieved_ids=[d.doc_id for d in own_docs[career_id]], duration_ms=duration_ms))
    return Explanations(
        source="llm" if any(i.source == "llm" for i in items) else "template",
        status="ready",
        items=items,
        trace=System2Trace(provider=provider.name, model=provider.model, retrieval=retrieval, careers=careers,
                           guardrail_hits=hits, duration_ms=round((time.perf_counter() - started) * 1000)),
    )
