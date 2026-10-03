"""Application errors and their HTTP mapping.

Every error response has the shape `{"error": {"code", "message", "details"}}` so the
frontend can handle failures in one place (frontend/src/api/client.ts).
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

VALIDATION_MESSAGE = "Some fields are invalid."


class AppError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFound(AppError):
    status_code = 404
    code = "not_found"


class InvalidInput(AppError):
    """Input that passed schema validation but fails a check needing data (e.g. unknown
    locality). Same shape as request validation errors, so the UI handles both one way."""

    status_code = 422
    code = "validation_error"

    def __init__(self, loc: list[str], msg: str) -> None:
        super().__init__(VALIDATION_MESSAGE, details={"fields": [{"loc": loc, "msg": msg}]})


class NotImplementedYet(AppError):
    """Raised by scaffolded code. `feature_id` points at the matching CHECKLIST.md row."""

    status_code = 501
    code = "not_implemented"

    def __init__(self, feature_id: str, what: str) -> None:
        super().__init__(
            f"{what} is not implemented yet (CHECKLIST.md {feature_id}).",
            details={"feature_id": feature_id},
        )


class SearchBudgetExceeded(AppError):
    """A live SerpApi call would exceed the per-run or monthly search budget."""

    status_code = 429
    code = "search_budget_exceeded"


class ReplayMiss(AppError):
    """Replay mode was asked for a response that has no recorded fixture."""

    status_code = 503
    code = "replay_miss"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            {
                "loc": [str(part) for part in err["loc"]],
                "msg": err["msg"].removeprefix("Value error, "),
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": VALIDATION_MESSAGE,
                    "details": {"fields": fields},
                }
            },
        )
