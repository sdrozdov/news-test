"""Authentication routes — WorkOS AuthKit hosted sign-in via sealed-session cookies.

Flow: the SPA sends the browser to ``/api/auth/login`` → WorkOS hosted page →
back to ``/api/auth/callback`` which sets the ``wos_session`` cookie and redirects
to the app. ``/api/auth/me`` reports the current user; ``/api/auth/logout`` clears
the cookie and returns the WorkOS logout URL.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.clients.auth_client import WorkOSAuth
from app.config import Settings
from app.dependencies import (
    COOKIE_NAME,
    get_auth,
    get_current_user,
    get_settings_dep,
    set_session_cookie,
)
from app.schemas.user import UserRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login(
    screen_hint: str | None = Query(default=None, pattern="^(sign-in|sign-up)$"),
    auth: WorkOSAuth = Depends(get_auth),
) -> RedirectResponse:
    """Redirect to WorkOS AuthKit. ``screen_hint=sign-up`` opens registration."""
    return RedirectResponse(url=auth.authorization_url(screen_hint))


@router.get("/callback")
async def callback(
    request: Request,
    code: str | None = Query(default=None),
    auth: WorkOSAuth = Depends(get_auth),
    settings: Settings = Depends(get_settings_dep),
) -> RedirectResponse:
    """AuthKit redirects here with a short-lived code; exchange it for a session."""
    base = settings.app_base_url or "/"
    if not code:
        return RedirectResponse(url=f"{base}?auth_error=1")
    try:
        sealed, _user = await auth.authenticate_with_code(code)
    except Exception:  # noqa: BLE001 - any code-exchange failure → graceful sign-in error
        logger.info("WorkOS code exchange failed", exc_info=True)
        return RedirectResponse(url=f"{base}?auth_error=1")
    response = RedirectResponse(url=base)
    set_session_cookie(response, sealed, settings)
    return response


@router.get("/me", response_model=UserRead)
async def me(user: UserRead = Depends(get_current_user)) -> UserRead:
    """The current signed-in user (401 if not authenticated)."""
    return user


@router.post("/logout")
async def logout(
    request: Request,
    auth: WorkOSAuth = Depends(get_auth),
    settings: Settings = Depends(get_settings_dep),
) -> JSONResponse:
    """End the session and send the SPA back to its own login screen.

    Revokes the WorkOS session server-side (via the API, no browser bounce to a
    hosted logout page) so the SSO session is truly ended, then clears the app's
    session cookie. The SPA navigates to the returned URL, where the now-401
    ``/me`` shows the sign-in gate. Revoke is best-effort — logout must not fail.
    """
    sealed = request.cookies.get(COOKIE_NAME)
    if sealed and settings.auth_enabled:
        try:
            await auth.revoke_session(sealed)
        except Exception:  # noqa: BLE001 - logout still succeeds if revoke fails
            logger.info("WorkOS session revoke failed", exc_info=True)
    response = JSONResponse({"logout_url": settings.app_base_url or "/"})
    # Match the attributes the cookie was set with so it clears in every deploy.
    response.delete_cookie(
        COOKIE_NAME,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )
    return response
