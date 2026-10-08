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
    DemoCacheEntry,
    Explanations,
    PipelineResult,
    WhatIfRequest,
    WhatIfResult,
)
from app.rag.templates import template_explanations
from app.settings import get_settings


def _explain(result: PipelineResult, request: AssessRequest) -> Explanations:
    data = get_dataset()
    return template_explanations(result, {c.id: c.name for c in data.cities}, request.student.home_city,
                                 request.parent.annual_income_inr)


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


def explanations(assessment_id: str) -> Explanations | None:
    """§13 explanations for a saved assessment (template text until System 2 is built)."""
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
