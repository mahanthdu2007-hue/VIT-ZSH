from fastapi import APIRouter

from app.engine.system1 import get_decision_model
from app.models.schemas import HealthResponse
from app.settings import get_settings

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        system1=get_decision_model().name,
        llm=settings.llm_provider,
        demo_mode=settings.demo_mode,
    )
