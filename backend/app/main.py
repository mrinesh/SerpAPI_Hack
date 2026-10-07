"""FastAPI application factory. Run with `make backend` (uvicorn app.main:app --reload)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.router import api_router
from app.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.db.session import SessionLocal, init_db
from app.jobs.scheduler import shutdown_scheduler, start_scheduler
from app.services.profiles import seed_demo_profiles


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    init_db()
    if get_settings().seed_demo_profiles:
        with SessionLocal() as db:
            seed_demo_profiles(db)
    if get_settings().scheduler_enabled:
        start_scheduler()
    yield
    shutdown_scheduler()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Realty Intel API",
        version=__version__,
        description="SerpApi-powered research and recommendations for real-estate investors.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
