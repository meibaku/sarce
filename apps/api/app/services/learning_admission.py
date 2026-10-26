"""Secure, balanced admission for the controlled Learning Evidence pilot."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.db.supabase import get_supabase

ARMS = ("experimental", "active_control")


def token_digest(token: str) -> str:
    """Return the stable lookup digest; plaintext invitation tokens are never stored."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def prepare_invite_batch(
    *, created_by: str, count: int, protocol_version: int, cohort: str,
    expires_in_hours: int, now: datetime | None = None,
) -> tuple[dict, list[dict], list[str]]:
    """Create an evenly assigned, cryptographically shuffled batch and one-time tokens."""
    if count < 2 or count > 200 or count % 2:
        raise ValueError("invite count must be an even number from 2 through 200")
    if protocol_version < 1 or cohort not in {"qualitative", "controlled"}:
        raise ValueError("invalid protocol version or cohort")
    if not 1 <= expires_in_hours <= 24 * 30:
        raise ValueError("expiry must be between 1 hour and 30 days")

    created_at = now or datetime.now(timezone.utc)
    expires_at = created_at + timedelta(hours=expires_in_hours)
    batch_id = str(uuid4())
    arms = [arm for arm in ARMS for _ in range(count // 2)]
    secrets.SystemRandom().shuffle(arms)
    tokens = [secrets.token_urlsafe(32) for _ in range(count)]
    batch = {
        "id": batch_id,
        "created_by": created_by,
        "protocol_version": protocol_version,
        "cohort": cohort,
        "invite_count": count,
        "expires_at": expires_at.isoformat(),
        "created_at": created_at.isoformat(),
    }
    invites = [
        {
            "id": str(uuid4()), "batch_id": batch_id, "token_hash": token_digest(token),
            "arm": arm, "expires_at": expires_at.isoformat(), "created_at": created_at.isoformat(),
        }
        for token, arm in zip(tokens, arms, strict=True)
    ]
    return batch, invites, tokens


class LearningAdmissionStore:
    """Persist invitation admission while keeping assignment and tokens server-side."""

    def create_batch(self, batch: dict, invites: list[dict]) -> None:
        get_supabase().rpc(
            "create_learning_invite_batch", {"p_batch": batch, "p_invites": invites}
        ).execute()

    def enroll(self, *, token: str, user_id: str, adult_confirmed: bool, consented_at: datetime) -> dict:
        data = get_supabase().rpc("redeem_learning_invite", {
            "p_token_hash": token_digest(token), "p_user_id": user_id,
            "p_adult_confirmed": adult_confirmed, "p_consented_at": consented_at.isoformat(),
        }).execute().data
        if isinstance(data, list):
            return data[0]
        return data

    def status(self, user_id: str) -> dict | None:
        rows = (
            get_supabase().table("learning_enrollments").select("*")
            .eq("user_id", user_id).limit(1).execute().data or []
        )
        return rows[0] if rows else None

    def withdraw(self, user_id: str, withdrawn_at: datetime) -> dict | None:
        rows = (
            get_supabase().table("learning_enrollments")
            .update({"withdrawn_at": withdrawn_at.isoformat()})
            .eq("user_id", user_id).is_("withdrawn_at", "null").execute().data or []
        )
        return rows[0] if rows else self.status(user_id)
