"""Shared response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """The uniform error envelope returned for every non-2xx response."""

    detail: str
    code: str


# Reusable OpenAPI `responses` fragments so error shapes are documented.
NOT_FOUND_RESPONSE = {404: {"model": ErrorResponse, "description": "Result not found"}}
UPSTREAM_RESPONSES = {
    429: {"model": ErrorResponse, "description": "Upstream rate limit reached"},
    502: {"model": ErrorResponse, "description": "Upstream provider error"},
    503: {"model": ErrorResponse, "description": "Integration not configured"},
}
