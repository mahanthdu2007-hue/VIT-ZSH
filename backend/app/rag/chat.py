"""§17 Ask PRISM: answers questions about one saved assessment.

Per message: care check → rule-based router (career names, cities, amounts) → engine work (What-If runs the real
engine) → a template answer built only from engine values → the LLM may reword it from CONTEXT → the §12 numeric
guardrail removes any sentence with an unsupported number. With LLM_PROVIDER=none or any failure, the template
answer is used, so the chat works offline.
"""

import json
import re
from typing import Any

from app.engine import config
from app.engine.formatting import format_inr, points
from app.engine.whatif import run_whatif
from app.models.schemas import (
    AssessmentInputs,
    AssessmentResult,
    CareerDetail,
    ChatIntent,
    ChatMessage,
    ChatReply,
    ChatRequest,
    ChatRoute,
    ChatWhatIf,
    Dataset,
    Explanations,
    GuardrailHit,
    WhatIfOverrides,
)
from app.rag import guardrail
from app.rag.index import citation, dataset_documents
from app.rag.llm import LLMError, Provider
from app.rag.templates import detail_doc_ids

CARE_WORDS = re.compile(r"\b(suicid\w*|kill myself|end my life|self[- ]?harm|hurt myself|want to die|can'?t go on|"
                        r"unbearable|hopeless|no reason to live|depressed)\b", re.IGNORECASE)
WHATIF_WORDS = re.compile(r"\b(what if|what happens if|if (we|our|i|my|the)|suppose|instead|change|reduce|increase|"
                          r"lower|raise|only have|can only)\b", re.IGNORECASE)
INTENT_WORDS: list[tuple[ChatIntent, re.Pattern[str]]] = [
    ("scholarships", re.compile(r"\b(scholarships?|aid|grants?|funding|exams?|entrance)\b", re.IGNORECASE)),
    ("plan", re.compile(r"\b(learn|skills?|plan|roadmap|start|first step|prepare|timeline|study)\b", re.IGNORECASE)),
    ("compare", re.compile(r"\b(compare|vs\.?|versus|better than|difference between|or)\b", re.IGNORECASE)),
    ("explain", re.compile(r"\b(why|explain|ranked?|score|fit|not|how)\b", re.IGNORECASE)),
]
TOP_WORDS = re.compile(r"(#\s*1\b|\bnumber one\b|\btop (career|choice|one)\b|\branked first\b|\bfirst\b)", re.IGNORECASE)
MONEY_WORDS = re.compile(r"(₹|\brs\b|\blakh|\blac|\bbudget|\bafford|\bspend|\bcost)", re.IGNORECASE)


# ---------------------------------------------------------------- routing
def _mentioned_careers(message: str, data: Dataset) -> list[str]:
    text = message.lower()
    found = [(text.find(c.name.lower()), c.id) for c in data.careers if c.name.lower() in text]
    found += [(text.find(c.id.replace("_", " ")), c.id) for c in data.careers
              if c.id.replace("_", " ") in text and c.name.lower() not in text]
    return list(dict.fromkeys(cid for _, cid in sorted(found)))


def parse_amount(message: str) -> int | None:
    """The first money amount in the message: 3 lakh, ₹3,00,000, 3L, 300000, Rs 3.5 lakh."""
    for token in guardrail.extract_numbers(message):
        amount = token.value * token.multiplier
        if amount >= 1000:
            return round(amount)
    return None


def _overrides(message: str, request: ChatRequest, data: Dataset) -> WhatIfOverrides:
    text = message.lower()
    values: dict[str, Any] = {}
    amount = parse_amount(message)
    if amount is not None and MONEY_WORDS.search(message):
        values["budget"] = amount
    if re.search(r"\bno loan|without (a )?loan|don'?t want (a )?loan", text):
        values["loan_willingness"] = "none"
    elif re.search(r"\b(big|large|high|full|bigger) loan|loan.*\b(high|more)\b", text):
        values["loan_willingness"] = "high"
    elif "loan" in text:
        values["loan_willingness"] = "moderate"
    for city in data.cities:
        if city.name.lower() in text or city.id.replace("_", " ") in text:
            values["home_city"] = city.id
            break
    if re.search(r"\b(relocate|move away|move to another|anywhere in india|move out)\b", text):
        values["willing_to_relocate"] = not re.search(r"\b(not|don'?t|won'?t|never)\b", text)
    level = re.search(r"\b(low|medium|high)[- ]risk\b", text)
    if level:
        values["risk_appetite" if request.asking_as == "parent" else "risk_tolerance"] = level.group(1)
    if re.search(r"\b(higher stud\w*|masters?|post ?grad\w*|pg)\b", text):
        values["wants_higher_studies"] = not re.search(r"\b(no|not|don'?t|without)\b", text)
    priority = re.search(r"\b(stability|salary|prestige|happiness)\b", text)
    if priority and re.search(r"\b(priority|prioriti[sz]e|care (most )?about|matters?|focus)\b", text):
        values["top_priority"] = priority.group(1)
    return WhatIfOverrides(**values)


def route(request: ChatRequest, result: AssessmentResult, data: Dataset) -> ChatRoute:
    """§17 step 2 rule-based router (the offline router; also used online, see DECISIONS.md)."""
    message = request.message
    if CARE_WORDS.search(message):
        return ChatRoute(intent="care", career_ids=[], overrides=WhatIfOverrides())
    careers = _mentioned_careers(message, data)
    if not careers and TOP_WORDS.search(message) and result.ranking:
        careers = [result.ranking[0].career_id]
    overrides = _overrides(message, request, data)
    if overrides.model_dump(exclude_none=True) and (WHATIF_WORDS.search(message) or "budget" in message.lower()):
        return ChatRoute(intent="whatif", career_ids=careers, overrides=overrides)
    intent: ChatIntent = "other"
    for name, pattern in INTENT_WORDS:
        if pattern.search(message) and (name != "compare" or len(careers) >= 2):
            intent = name
            break
    if intent == "other" and careers:
        intent = "explain"
    if not careers and intent in ("explain", "plan", "scholarships"):
        fallback = request.selected_career_id or (result.ranking[0].career_id if result.ranking else None)
        careers = [fallback] if fallback else []
    return ChatRoute(intent=intent, career_ids=careers, overrides=WhatIfOverrides())


# ---------------------------------------------------------------- template answers (engine values only)
def _career_line(result: AssessmentResult, career_id: str, names: dict[str, str]) -> str:
    ranked = next((r for r in result.ranking if r.career_id == career_id), None)
    if ranked is None:
        return (f"{names.get(career_id, career_id)} is not in your top careers, so the results do not include its "
                f"full score. Changing the budget or loan answers in a what-if may bring it in.")
    parts = ", ".join(f"{config.COMPONENT_LABELS[k]} {points(k, v)}" for k, v in ranked.points.items())
    return f"{ranked.name} is ranked #{ranked.rank} with a PRISM Score of {ranked.score:.1f} out of 100 ({parts})."


def _explain(result: AssessmentResult, explanations: Explanations, career_id: str, names: dict[str, str]) -> str:
    text = _career_line(result, career_id, names)
    item = next((i for i in explanations.items if i.career_id == career_id), None)
    if item is not None:
        text += " " + " ".join(item.why[:2])
    if result.middle_path and result.middle_path.career_id == career_id:
        text += " It is also the family's middle path."
    return text


def _whatif_answer(changes: ChatWhatIf, names: dict[str, str]) -> str:
    o = changes.overrides.model_dump(exclude_none=True)
    described = ", ".join(f"{k.replace('_', ' ')} {format_inr(v) if k == 'budget' else v}" for k, v in o.items())
    top = changes.result.ranking[:3]
    text = (f"With {described}, the engine re-ranked your careers. New top 3: "
            + "; ".join(f"#{r.rank} {r.name} ({r.score:.1f})" for r in top) + ".")
    reasons = [c.reason for c in changes.result.changes if c.reason][:2]
    if reasons:
        text += " " + " ".join(reasons)
    else:
        moved = [c for c in changes.result.changes if c.rank_before and c.rank_before <= 5][:3]
        text += " " + " ".join(f"{c.name}: {c.score_before:.1f} → {c.score_after:.1f}." for c in moved)
    return text


def _scholarships(d: CareerDetail) -> str:
    if d.scholarships:
        schemes = "; ".join(f"{s.name} (up to {format_inr(s.amount_inr_per_year)} a year"
                            + (f", only for {s.restricted_to})" if s.restricted_to else ")")
                            for s in d.scholarships[:3])
        text = f"For {d.career.name} via {d.pathway.label}, schemes that match your family income: {schemes}."
    else:
        text = f"No scheme in our list matches {d.career.name} via {d.pathway.label} at your family income."
    if d.exams:
        text += " Entrance exams: " + "; ".join(f"{e.name} (usually {e.typical_month})" for e in d.exams[:3]) + "."
    return text + " Amounts are indicative estimates; check each scheme's official portal."


def _plan(d: CareerDetail) -> str:
    gaps = [g for g in d.skill_plan.gaps if g.gap > 0][:3]
    text = f"For {d.career.name}, the suggested route is {d.pathway.label}: {' → '.join(d.pathway.steps)}."
    if gaps:
        text += " Learn first: " + "; ".join(
            f"{g.skill} ({g.current:.0%} now, {g.level_required:.0%} needed)" for g in gaps) + "."
    else:
        text += " Your current skills already meet this career's levels; keep building projects."
    return text


def _other(result: AssessmentResult) -> str:
    top = result.ranking[0].name if result.ranking else "your top career"
    return (f"I can answer questions about your results, like why {top} is ranked first, what changes if the "
            f"budget changes, which scholarships fit, or what to learn first. Could you ask about one of those?")


def _care() -> str:
    return ("I'm really sorry you're feeling this way. You don't have to handle it alone. Please talk to someone you "
            "trust, like a parent, a teacher or your school counsellor. You can also call "
            f"{config.CARE_HELPLINE}, India's free mental-health helpline, any time of day.")


# ---------------------------------------------------------------- CONTEXT for the LLM
def _detail_context(d: CareerDetail) -> dict[str, Any]:
    return {"career": d.career.name, "rank": d.rank, "status": d.status, "score": d.score.score,
            "route": d.pathway.label, "steps": d.pathway.steps, "years": d.pathway.duration_years,
            "cost_after_scholarship": format_inr(d.finance.effective_cost or 0),
            "funding_gap": format_inr(d.finance.funding_gap),
            "skill_gaps": [{"skill": g.skill, "now": f"{g.current:.0%}", "needed": f"{g.level_required:.0%}"}
                           for g in d.skill_plan.gaps if g.gap > 0][:4],
            "timeline": [{"year": t.year, "steps": t.steps} for t in d.skill_plan.timeline],
            "payback_years": round(d.roi.break_even_years, 1),
            "risk_radar": {k: round(v, 2) for k, v in d.risk.model_dump().items() if k != "career_id"},
            "best_city": d.market.best_city,
            "scholarships": [{"name": s.name, "per_year": format_inr(s.amount_inr_per_year)} for s in d.scholarships],
            "exams": [{"name": e.name, "month": e.typical_month} for e in d.exams]}


def build_context(result: AssessmentResult, inputs: AssessmentInputs, route_: ChatRoute,
                  whatif: ChatWhatIf | None, history: list[ChatMessage]) -> dict[str, Any]:
    """§17 step 1 compact CONTEXT: inputs, ranking with points, details for mentioned careers, family view."""
    student = inputs.student.model_dump(mode="json")
    parent = inputs.parent.model_dump(mode="json")
    for answers in (student, parent):
        for key in [k for k in answers if k.startswith("free_text")]:
            answers[key] = (answers[key] or "")[:config.CHAT_FREE_TEXT_CHARS]
        for key in ("aptitude_answers", "riasec_answers", "workstyle_answers", "skill_ratings"):
            answers.pop(key, None)
    detail_ids = [c for c in route_.career_ids if c in result.details][:3]
    context: dict[str, Any] = {
        "student": student, "parent": parent,
        "ranking": [{"rank": r.rank, "career": r.name, "score": r.score,
                     "points": {config.COMPONENT_LABELS[k]: round(v, 1) for k, v in r.points.items()}}
                    for r in result.ranking[:10]],
        "details": {c: _detail_context(result.details[c]) for c in detail_ids},
        "conflict_index": result.conflict.index, "conflict_hotspots": result.conflict.hotspots,
        "middle_path": result.middle_path.career_id if result.middle_path else None,
        "stretch_options": [s.career_id for s in result.stretch_options],
        "swot": result.swot.model_dump() if result.swot else None,
        "history": [{"who": m.who, "text": m.text} for m in history[-config.CHAT_HISTORY_TURNS:]],
    }
    if whatif is not None:
        context["whatif"] = {"overrides": whatif.overrides.model_dump(exclude_none=True),
                             "new_top_5": [{"rank": r.rank, "career": r.name, "score": r.score}
                                           for r in whatif.result.ranking[:5]],
                             "reasons": [c.reason for c in whatif.result.changes if c.reason][:5]}
    return context


def _system_prompt(asking_as: str) -> str:
    reader = "a parent of an Indian student" if asking_as == "parent" else "an Indian school or college student"
    return (f"You are Ask PRISM, answering {reader} about their own career results. Rules: answer only from "
            f"CONTEXT and FACTS; every number must be copied exactly from them, never calculated; at most "
            f"{config.CHAT_MAX_WORDS} words; plain warm language; if something is not in the results, say so and "
            "name the input that would help; never promise admission, salary or outcomes; politely steer "
            "off-topic questions back to career planning. FACTS is the engine's answer: keep all of it correct. "
            "Write plain sentences with no markdown, lists or symbols like ** or `. Never mention CONTEXT, FACTS, "
            "fields or JSON, and never ask for answers the family already gave.")


def _checked(answer: str, allowed: set[float], hits: list[GuardrailHit]) -> str:
    kept = []
    for sentence in guardrail.split_sentences(answer):
        bad = guardrail.unsupported_numbers(sentence, allowed)
        if bad:
            hits.append(GuardrailHit(career_id="", field="answer", sentence=sentence, unsupported=bad,
                                     action="removed", replacement=None))
        else:
            kept.append(sentence)
    return " ".join(kept)


# ---------------------------------------------------------------- one message
def answer(request: ChatRequest, result: AssessmentResult, inputs: AssessmentInputs, explanations: Explanations,
           history: list[ChatMessage], data: Dataset, provider: Provider) -> ChatReply:
    names = {c.id: c.name for c in data.careers}
    route_ = route(request, result, data)
    if route_.intent == "care":  # §17 care rule: no career advice in this reply
        return ChatReply(answer=_care(), intent="care", sources=[], whatif=None, guardrail_hits=[], provider="none")

    whatif: ChatWhatIf | None = None
    doc_ids: list[str] = []
    if route_.intent == "whatif":
        whatif = ChatWhatIf(overrides=route_.overrides,
                            result=run_whatif(inputs.student, inputs.parent, inputs.decisions, route_.overrides, data,
                                              inputs.as_of, request.assessment_id))
        facts = _whatif_answer(whatif, names)
    elif route_.intent == "compare":
        facts = " ".join(_career_line(result, c, names) for c in route_.career_ids[:2])
    elif route_.intent in ("explain", "plan", "scholarships") and route_.career_ids:
        career_id = route_.career_ids[0]
        d = result.details.get(career_id)
        if route_.intent == "explain" or d is None:
            facts = _explain(result, explanations, career_id, names)
        else:
            facts = _plan(d) if route_.intent == "plan" else _scholarships(d)
    else:
        facts = _other(result)
    for career_id in route_.career_ids[:2]:
        d = result.details.get(career_id)
        doc_ids += detail_doc_ids(d) if d else ([f"career:{career_id}"] if f"career:{career_id}" in
                                                 dataset_documents() else [])
    sources = [citation(doc_id) for doc_id in dict.fromkeys(doc_ids)]

    context = build_context(result, inputs, route_, whatif, history)
    hits: list[GuardrailHit] = []
    text, used = facts, "none"
    if provider.name != "none" and route_.intent != "other":
        user = (f"CONTEXT:\n{json.dumps(context, ensure_ascii=False, default=str)}\n\nFACTS:\n{facts}\n\n"
                f"QUESTION:\n{request.message}")
        try:
            worded = provider.complete_text(_system_prompt(request.asking_as), user, timeout_s=config.CHAT_TIMEOUT_S)
            plain = re.sub(r"\s+", " ", re.sub(r"[*`#]+", "", worded))
            checked = _checked(plain, guardrail.allowed_values(context, [facts]), hits)
            if checked:
                text, used = checked, provider.name
        except LLMError:
            pass
    return ChatReply(answer=text, intent=route_.intent, sources=sources, whatif=whatif, guardrail_hits=hits,
                     provider=used)
