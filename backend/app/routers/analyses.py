"""The analysis result resource: create (analyze + store), list, get, delete.

Every route is scoped to the signed-in user (via ``get_current_user``), so a user
only ever sees and manages their own saved results.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.dependencies import get_analysis_service, get_current_user
from app.schemas.analysis import AnalysisRead, AnalyzeRequest
from app.schemas.common import NOT_FOUND_RESPONSE, UPSTREAM_RESPONSES
from app.schemas.user import UserRead
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.post(
    "",
    response_model=AnalysisRead,
    status_code=status.HTTP_201_CREATED,
    responses=UPSTREAM_RESPONSES,
)
async def create_analysis(
    payload: AnalyzeRequest,
    response: Response,
    service: AnalysisService = Depends(get_analysis_service),
    user: UserRead = Depends(get_current_user),
) -> AnalysisRead:
    """Analyze the selected article (summary + sentiment) and store the result.

    Returns 201 when a new result is created and 200 when an existing one
    (same article URL for this user) is re-analyzed in place.
    """
    analysis, created = await service.analyze_and_store(user.id, payload.article)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    response.headers["Location"] = f"/api/analyses/{analysis.id}"
    return analysis


@router.get("", response_model=list[AnalysisRead])
async def list_analyses(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, max_length=200, description="Filter saved summaries"),
    service: AnalysisService = Depends(get_analysis_service),
    user: UserRead = Depends(get_current_user),
) -> list[AnalysisRead]:
    return await service.list_results(user.id, limit=limit, offset=offset, query=q)


@router.get("/{analysis_id}", response_model=AnalysisRead, responses=NOT_FOUND_RESPONSE)
async def get_analysis(
    analysis_id: UUID,
    service: AnalysisService = Depends(get_analysis_service),
    user: UserRead = Depends(get_current_user),
) -> AnalysisRead:
    return await service.get_result(user.id, analysis_id)


@router.delete(
    "/{analysis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=NOT_FOUND_RESPONSE,
)
async def delete_analysis(
    analysis_id: UUID,
    response: Response,
    service: AnalysisService = Depends(get_analysis_service),
    user: UserRead = Depends(get_current_user),
) -> Response:
    # Set 204 on the shared injected response (not a fresh one) so a session
    # cookie refreshed inside get_current_user is preserved.
    await service.delete_result(user.id, analysis_id)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
