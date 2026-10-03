from fastapi import APIRouter

from app import __version__
from app.api.deps import AppSettings
from app.schemas.views import HealthStatus

router = APIRouter(tags=["meta"])


@router.get("/health")
def health(settings: AppSettings) -> HealthStatus:
    return HealthStatus(
        status="ok",
        version=__version__,
        serpapi_mode=settings.serpapi_mode,
        llm_mode=settings.llm_mode,
        city=settings.default_city,
    )
