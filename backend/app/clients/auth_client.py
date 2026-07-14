"""WorkOS AuthKit adapter — hosted sign-in with sealed-session cookies.

Wraps the WorkOS Python SDK so the rest of the app depends on a small capability,
not the vendor. The SDK is synchronous, so its network calls run in a threadpool
to avoid blocking the event loop. The SDK client is created lazily, so the app
boots without WorkOS credentials; when absent the app runs in local "dev mode"
(see ``dependencies.get_current_user``) and these methods are never called.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from starlette.concurrency import run_in_threadpool

from app.config import Settings
from app.errors import AppError

logger = logging.getLogger(__name__)


@dataclass
class AuthUser:
    id: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    profile_picture_url: str | None = None


class WorkOSAuth:
    """Thin wrapper over the ``workos`` AuthKit session-management helpers."""

    def __init__(self, settings: Settings, client=None) -> None:
        self._settings = settings
        self._client = client

    def _get_client(self):
        if self._client is None:
            if not self._settings.auth_enabled:
                raise AppError(
                    "Authentication is not configured (set WORKOS_* env vars).",
                    status_code=503,
                    code="auth_not_configured",
                )
            from workos import WorkOSClient

            self._client = WorkOSClient(
                api_key=self._settings.workos_api_key,
                client_id=self._settings.workos_client_id,
            )
        return self._client

    def authorization_url(self, screen_hint: str | None = None) -> str:
        # Builds a URL locally (no network), so it stays synchronous.
        kwargs: dict = {
            "provider": "authkit",
            "redirect_uri": self._settings.workos_redirect_uri,
        }
        if screen_hint:
            kwargs["screen_hint"] = screen_hint
        return self._get_client().user_management.get_authorization_url(**kwargs)

    async def authenticate_with_code(self, code: str) -> tuple[str, AuthUser]:
        client = self._get_client()
        resp = await run_in_threadpool(
            lambda: client.user_management.authenticate_with_code(
                code=code,
                session={
                    "seal_session": True,
                    "cookie_password": self._settings.workos_cookie_password,
                },
            )
        )
        return resp.sealed_session, _to_user(resp.user)

    async def load_user(self, sealed_session: str) -> tuple[AuthUser | None, str | None]:
        """Validate a sealed session → ``(user, refreshed_sealed_session)``.

        The second value is non-None only when the token was refreshed and the
        caller should update the cookie; ``(None, None)`` means invalid/expired.
        """
        return await run_in_threadpool(self._load_user_sync, sealed_session)

    def _load_user_sync(self, sealed_session: str) -> tuple[AuthUser | None, str | None]:
        client = self._get_client()
        session = client.user_management.load_sealed_session(
            sealed_session=sealed_session,
            cookie_password=self._settings.workos_cookie_password,
        )
        result = session.authenticate()
        if getattr(result, "authenticated", False):
            return _to_user(result.user), None
        try:
            refreshed = session.refresh()
        except Exception:  # noqa: BLE001 - refresh is best-effort
            logger.debug("Session refresh failed", exc_info=True)
            return None, None
        if getattr(refreshed, "authenticated", False):
            return _to_user(refreshed.user), getattr(refreshed, "sealed_session", None)
        return None, None

    async def revoke_session(self, sealed_session: str) -> None:
        """End the WorkOS session server-side (proper logout).

        Revokes the session via the WorkOS API using the id inside the sealed
        session — no browser redirect to a hosted logout page. After this the
        SSO session is gone, so the next sign-in re-prompts for credentials.
        """
        await run_in_threadpool(self._revoke_session_sync, sealed_session)

    def _revoke_session_sync(self, sealed_session: str) -> None:
        client = self._get_client()
        session = client.user_management.load_sealed_session(
            sealed_session=sealed_session,
            cookie_password=self._settings.workos_cookie_password,
        )
        result = session.authenticate()
        session_id = getattr(result, "session_id", None)
        if not session_id:
            # Access token expired — refresh to recover the session id, then revoke.
            try:
                refreshed = session.refresh()
                session_id = getattr(refreshed, "session_id", None)
            except Exception:  # noqa: BLE001 - best-effort; fall through to no-op
                session_id = None
        if session_id:
            client.user_management.revoke_session(session_id=session_id)


def _to_user(user) -> AuthUser:
    return AuthUser(
        id=user.id,
        email=getattr(user, "email", None),
        first_name=getattr(user, "first_name", None),
        last_name=getattr(user, "last_name", None),
        profile_picture_url=getattr(user, "profile_picture_url", None),
    )
