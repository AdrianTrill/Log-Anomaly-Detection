from fastapi import APIRouter
from app.core.config import settings
from app.models.schemas import HealthResponse
from app.services.model_registry import registry

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        models=registry.list_models(),
    )
