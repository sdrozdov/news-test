"""The authenticated user, as exposed to the API and derived from WorkOS."""

from __future__ import annotations

from pydantic import BaseModel


class UserRead(BaseModel):
    """Public shape of the signed-in user."""

    id: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    profile_picture_url: str | None = None
