"""Resolve user context for local-first dev."""

from __future__ import annotations

from app.config import settings


def resolve_user_id(user_id: str | None) -> str:
    """Use explicit user_id or fall back to LOCAL_USER_ID from .env."""
    return user_id or settings.local_user_id
