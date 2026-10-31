"""
Resolve who is calling.

Local-first by default: with no sign-in, requests act as `LOCAL_USER_ID`. When a request
carries a Supabase access token it is verified and **that** user is used everywhere — a
`user_id` sent by the client is then ignored. `AUTH_REQUIRED=true` turns the token from
optional into mandatory (docs/CHAOS_PLAN.md, M8).
"""

from __future__ import annotations

from contextvars import ContextVar

from fastapi import Header, HTTPException

from app.config import settings
from app.db.supabase import get_supabase
from app.services.pilot_policy import PilotPolicy

# Set per request by `authenticate`; None means "not signed in".
_current_user: ContextVar[str | None] = ContextVar("sarce_current_user", default=None)


def current_user_id() -> str | None:
    """The verified signed-in user for this request, if any."""
    return _current_user.get()


async def authenticate(authorization: str | None = Header(default=None)) -> None:
    """Router dependency: verify the bearer token, or reject when sign-in is required."""
    _current_user.set(None)
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        if settings.auth_required:
            raise HTTPException(status_code=401, detail="Sign in required")
        return
    try:
        # Ask Supabase Auth; never trust claims we have not had verified.
        user = get_supabase().auth.get_user(token.strip()).user
        user_id = str(user.id)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from exc
    _current_user.set(user_id)


def resolve_user_id(user_id: str | None) -> str:
    """The signed-in user if there is one; otherwise the explicit id or LOCAL_USER_ID."""
    return current_user_id() or user_id or settings.local_user_id


def scoped_user_id(user_id: str | None, username: str | None) -> str | None:
    """
    User filter for username-based reads.

    Signed in: always the caller, so a username alone can never reach someone else's
    games. Local-first: the original behaviour — filter by user only when one was given
    or no username was.
    """
    signed_in = current_user_id()
    if signed_in:
        return signed_in
    return resolve_user_id(user_id) if user_id or not username else None


def require_game_access(game_id: str) -> None:
    """When signed in, 404 unless the game belongs to the caller. No-op in local-first mode."""
    signed_in = current_user_id()
    if not signed_in:
        return
    res = (
        get_supabase().table("games").select("id").eq("id", game_id).eq("user_id", signed_in).limit(1).execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Game not found")


def require_pilot_admission() -> None:
    """Hosted pilot data routes fail closed until current consent exists."""
    if not PilotPolicy.current().enabled:
        return
    user = current_user_id()
    if not user:
        raise HTTPException(status_code=401, detail="Sign in required")
    from app.services.pilot import PilotService

    if not PilotService().admitted(user):
        raise HTTPException(status_code=403, detail="Pilot invitation and consent required")


def require_pilot_collection_active() -> None:
    """Reject pilot mutations after withdrawal, expiry, or the tenth read."""
    if not PilotPolicy.current().enabled:
        return
    user = current_user_id()
    if not user:
        raise HTTPException(status_code=401, detail="Sign in required")
    from app.services.pilot import PilotService

    if not PilotService().collection_active(user):
        raise HTTPException(status_code=409, detail="Pilot collection is read-only")


def require_capability(capability: str):
    """Build a FastAPI dependency for a named pilot capability."""
    def check() -> None:
        PilotPolicy.current().require(capability)

    return check
