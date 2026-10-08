"""Glue between the API and the engine: runs assessments and What-Ifs, saves and loads them."""

import uuid
from datetime import date, datetime

from app import demo_cache, storage
from app.engine.loader import get_dataset
from app.engine.pipeline import run_pipeline
from app.engine.system1 import get_decision_model, run_decisions
from app.engine.whatif import run_whatif
from app.models.schemas import (
    AssessmentInputs,
    AssessmentResult,
    AssessRequest,
    ChatHistory,
    ChatMessage,
    ChatReply,
    ChatRequest,
    DemoCacheEntry,
    Explanations,
    PipelineResult,
    WhatIfRequest,
    WhatIfResult,
)
from app.rag import chat
from app.rag.explain import llm_explanations
from app.rag.llm import get_llm
from app.rag.templates import template_explanations
from app.settings import get_settings


def _city_names() -> dict[str, str]:
    return {c.id: c.name for c in get_dataset().cities}


def _explain(result: PipelineResult, request: AssessRequest) -> Explanations:
    """Template text now; marked pending when an LLM will reword it in the background (§13 lazy load)."""
    templates = template_explanations(result, _city_names(), request.student.home_city,
                                      request.parent.annual_income_inr)
    return templates.model_copy(update={"status": "pending" if get_llm().name != "none" else "ready"})


def _run(request: AssessRequest) -> DemoCacheEntry:
    """The pipeline result, served from the demo cache when DEMO_MODE is on and the profile is a demo one."""
    data = get_dataset()
    profile_id = demo_cache.demo_profile_id(request, data) if get_settings().demo_mode else None
    if profile_id is not None:
        cached = demo_cache.load(profile_id, request)
        if cached is not None:
            return cached
    result = run_pipeline(request.student, request.parent, data, date.today(), model=get_decision_model())
    entry = DemoCacheEntry(decisions=result.trace.system1.decisions, result=result)
    if profile_id is not None:
        demo_cache.save(profile_id, request, entry)
    return entry


def assess(request: AssessRequest) -> AssessmentResult:
    entry = _run(request)
    result = entry.result
    assessment = AssessmentResult(id=str(uuid.uuid4()), explanations=_explain(result, request), **dict(result))
    inputs = AssessmentInputs(student=request.student, parent=request.parent, decisions=entry.decisions,
                              as_of=result.as_of)
    storage.save_assessment(inputs, assessment, datetime.now())
    return assessment


def write_explanations(assessment_id: str) -> None:
    """Background task: System 2 explanations for a saved assessment (§12). Never leaves them pending."""
    result, inputs = storage.load_result(assessment_id), storage.load_inputs(assessment_id)
    if result is None or inputs is None:
        return
    try:
        explained = llm_explanations(get_llm(), result, result.explanations, _city_names(), inputs.student,
                                     inputs.parent)
    except Exception:  # §2.4 an unexpected failure keeps the template text the student already sees
        explained = result.explanations.model_copy(update={"status": "ready"})
    storage.save_explanations(assessment_id, explained)


def explanations(assessment_id: str) -> Explanations | None:
    """§13 the LLM explanations when written, else the template text saved with the result."""
    saved = storage.load_explanations(assessment_id)
    if saved is not None:
        return saved
    result = storage.load_result(assessment_id)
    return None if result is None else result.explanations


def whatif(request: WhatIfRequest) -> WhatIfResult | None:
    """§11 What-If on a saved assessment (its System 1 decisions are reused) or on a full profile."""
    if request.assessment_id is not None:
        inputs = storage.load_inputs(request.assessment_id)
        if inputs is None:
            return None
    else:
        assert request.profile is not None
        student, parent = request.profile.student, request.profile.parent
        inputs = AssessmentInputs(student=student, parent=parent, as_of=date.today(),
                                  decisions=run_decisions(get_decision_model(), student, parent))
    return run_whatif(inputs.student, inputs.parent, inputs.decisions, request.overrides, get_dataset(),
                      inputs.as_of, request.assessment_id)


def chat_message(request: ChatRequest) -> ChatReply | None:
    """§17 one Ask PRISM message on a saved assessment; the question and reply are saved to its history."""
    result, inputs = storage.load_result(request.assessment_id), storage.load_inputs(request.assessment_id)
    if result is None or inputs is None:
        return None
    history = storage.load_chat_messages(request.assessment_id)
    current = explanations(request.assessment_id) or result.explanations
    reply = chat.answer(request, result, inputs, current, history, get_dataset(), get_llm())
    storage.save_chat_messages(request.assessment_id, [
        ChatMessage(who="user", text=request.message, asking_as=request.asking_as, reply=None),
        ChatMessage(who="assistant", text=reply.answer, asking_as=request.asking_as, reply=reply),
    ], datetime.now())
    return reply


def chat_history(assessment_id: str) -> ChatHistory | None:
    if storage.load_inputs(assessment_id) is None:
        return None
    return ChatHistory(assessment_id=assessment_id, messages=storage.load_chat_messages(assessment_id))
