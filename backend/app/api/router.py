"""Mounts every route module under /api. docs/API.md lists the endpoints."""

from fastapi import APIRouter

from app.api.routes import alerts, health, meta, portfolio, profiles, properties, runs

api_router = APIRouter()
for module in (health, meta, profiles, runs, properties, portfolio, alerts):
    api_router.include_router(module.router)
