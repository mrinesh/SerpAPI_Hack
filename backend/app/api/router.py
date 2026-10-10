"""Mounts every route module under /api. docs/API.md lists the endpoints."""

from fastapi import APIRouter, Depends

from app.api.deps import require_account
from app.api.routes import alerts, auth, health, meta, portfolio, profiles, properties, runs

api_router = APIRouter()
for module in (health, auth):
    api_router.include_router(module.router)
for module in (meta, profiles, runs, properties, portfolio, alerts):
    api_router.include_router(module.router, dependencies=[Depends(require_account)])
