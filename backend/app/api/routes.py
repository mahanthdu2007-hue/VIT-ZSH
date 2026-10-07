from fastapi import APIRouter

from app.models.schemas import HealthResponse
from app.settings import get_settings

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        system1="not_loaded",
        llm=settings.llm_provider,
        demo_mode=settings.demo_mode,
    )
