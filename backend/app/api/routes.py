from fastapi import APIRouter, HTTPException

from app import services
from app.engine.loader import get_dataset
from app.engine.system1 import get_decision_model
from app.models.schemas import (
    AssessmentResult,
    AssessRequest,
    Career,
    CareerSummary,
    DatasetCounts,
    DemoProfile,
    Explanations,
    HealthResponse,
    PublicQuestionSet,
    Track,
    WhatIfRequest,
    WhatIfResult,
)
from app.settings import get_settings

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    data = get_dataset()
    return HealthResponse(
        status="ok",
        system1=get_decision_model().name,
        llm=settings.llm_provider,
        demo_mode=settings.demo_mode,
        dataset=DatasetCounts(careers=len(data.careers), scholarships=len(data.scholarships), exams=len(data.exams),
                              cities=len(data.cities), demo_profiles=len(data.demo_profiles)),
    )


@router.get("/questions/{track}", response_model=PublicQuestionSet)
def questions(track: Track) -> PublicQuestionSet:
    data = get_dataset()
    question_set = data.questions_school if track == "school" else data.questions_college
    return PublicQuestionSet.model_validate(question_set.model_dump(exclude={"aptitude": {"__all__": {"answer"}}}))


@router.get("/demo-profiles", response_model=list[DemoProfile])
def demo_profiles() -> list[DemoProfile]:
    return get_dataset().demo_profiles


@router.post("/assess", response_model=AssessmentResult)
def assess(request: AssessRequest) -> AssessmentResult:
    return services.assess(request)


@router.post("/whatif", response_model=WhatIfResult)
def whatif(request: WhatIfRequest) -> WhatIfResult:
    result = services.whatif(request)
    if result is None:
        raise HTTPException(status_code=404, detail=f"assessment {request.assessment_id} not found")
    return result


@router.get("/explanations/{assessment_id}", response_model=Explanations)
def explanations(assessment_id: str) -> Explanations:
    result = services.explanations(assessment_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"assessment {assessment_id} not found")
    return result


@router.get("/careers", response_model=list[CareerSummary])
def careers() -> list[CareerSummary]:
    return [CareerSummary(id=c.id, name=c.name, domain=c.domain, steam=list(c.steam), summary=c.summary)
            for c in get_dataset().careers]


@router.get("/careers/{career_id}", response_model=Career)
def career(career_id: str) -> Career:
    found = next((c for c in get_dataset().careers if c.id == career_id), None)
    if found is None:
        raise HTTPException(status_code=404, detail=f"career {career_id} not found")
    return found
