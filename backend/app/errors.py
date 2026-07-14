"""Domain error hierarchy and the handlers that turn them into JSON responses.

Keeping errors as domain objects lets services stay HTTP-agnostic while still
producing accurate status codes and machine-readable ``code`` values at the edge.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Base class for expected, client-facing application errors."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class NewsAPIError(AppError):
    status_code = 502
    code = "news_api_error"


class AIServiceError(AppError):
    status_code = 502
    code = "ai_service_error"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"


def register_exception_handlers(app: FastAPI) -> None:
    """Register handlers so every error response shares the {detail, code} shape."""

    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code},
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        first = errors[0] if errors else {}
        loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        detail = f"{loc}: {first.get('msg', 'invalid')}" if loc else "Validation error."
        return JSONResponse(status_code=422, content={"detail": detail, "code": "validation_error"})

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": str(exc.detail), "code": "http_error"},
        )
