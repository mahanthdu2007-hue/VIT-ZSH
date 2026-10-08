from fastapi import APIRouter, BackgroundTasks, HTTPException

from app import services
from app.engine.loader import get_dataset
from app.engine.system1 import get_decision_model
from app.models.schemas import (
    AssessmentResult,
    AssessRequest,
    Career,
    CareerSummary,
    ChatHistory,
    ChatReply,
    ChatRequest,
    DatasetCounts,
    DemoProfile,
    Explanations,
    HealthResponse,
    PublicQuestionSet,
    Track,
    WhatIfRequest,
    WhatIfResult,
)
from app.rag.llm import llm_status
from app.settings import get_settings

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    data = get_dataset()
    llm = llm_status()
    return HealthResponse(
        status="ok",
        system1=get_decision_model().name,
        llm=llm.provider,
        llm_model=llm.model,
        llm_requested=llm.requested,
        llm_notes=llm.notes,
        demo_mode=get_settings().demo_mode,
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
def assess(request: AssessRequest, background: BackgroundTasks) -> AssessmentResult:
    result = services.assess(request)
    if result.explanations.status == "pending":  # §13 LLM text follows via GET /api/explanations/{id}
        background.add_task(services.write_explanations, result.id)
    return result


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


@router.post("/chat", response_model=ChatReply)
def chat(request: ChatRequest) -> ChatReply:
    reply = services.chat_message(request)
    if reply is None:
        raise HTTPException(status_code=404, detail=f"assessment {request.assessment_id} not found")
    return reply


@router.get("/chat/{assessment_id}", response_model=ChatHistory)
def chat_history(assessment_id: str) -> ChatHistory:
    history = services.chat_history(assessment_id)
    if history is None:
        raise HTTPException(status_code=404, detail=f"assessment {assessment_id} not found")
    return history
