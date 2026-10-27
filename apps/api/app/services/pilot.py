"""Durable admission and participant evidence for the style pilot."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.db.supabase import get_supabase
from app.services.pilot_policy import PilotPolicy


def token_hash(token: str) -> str:
    """Hash bearer invitations so a database read cannot reveal an unused token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class PilotService:
    def __init__(self, client=None):
        self.sb = client or get_supabase()

    def create_invitation(self, operator_id: str, hours: int = 168) -> dict:
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=hours)
        row = self.sb.table("pilot_invitations").insert(
            {"token_hash": token_hash(token), "expires_at": expires.isoformat(), "created_by": operator_id}
        ).execute().data[0]
        return {"id": row["id"], "token": token, "expiresAt": row["expires_at"]}

    def redeem(self, user_id: str, token: str) -> dict:
        now = datetime.now(timezone.utc)
        rows = self.sb.table("pilot_invitations").select("id, expires_at, redeemed_by").eq(
            "token_hash", token_hash(token)
        ).limit(1).execute().data or []
        if not rows:
            raise ValueError("Invitation is invalid")
        invitation = rows[0]
        if invitation.get("redeemed_by"):
            raise ValueError("Invitation has already been used")
        if datetime.fromisoformat(invitation["expires_at"].replace("Z", "+00:00")) <= now:
            raise ValueError("Invitation has expired")
        updated = self.sb.table("pilot_invitations").update(
            {"redeemed_by": user_id, "redeemed_at": now.isoformat()}
        ).eq("id", invitation["id"]).is_("redeemed_by", "null").execute().data or []
        if not updated:
            raise ValueError("Invitation has already been used")
        return {"redeemed": True}

    def consent(self, user_id: str, adult: bool, protocol: str, privacy: str) -> dict:
        if not adult:
            raise ValueError("The pilot is limited to adults aged 18 or older")
        if protocol != settings.pilot_protocol_version or privacy != settings.pilot_privacy_version:
            raise ValueError("The pilot terms have changed; review the current versions")
        invites = self.sb.table("pilot_invitations").select("id").eq("redeemed_by", user_id).limit(1).execute().data or []
        if not invites:
            raise ValueError("Redeem an invitation before consenting")
        row = {
            "user_id": user_id,
            "invitation_id": invites[0]["id"],
            "protocol_version": protocol,
            "privacy_version": privacy,
            "adult_confirmed": True,
            "withdrawn_at": None,
        }
        self.sb.table("pilot_consents").upsert(row, on_conflict="user_id").execute()
        return self.status(user_id)

    def admitted(self, user_id: str) -> bool:
        rows = self.sb.table("pilot_consents").select("user_id").eq("user_id", user_id).is_(
            "withdrawn_at", "null"
        ).limit(1).execute().data or []
        return bool(rows)

    def status(self, user_id: str) -> dict:
        consent = self.sb.table("pilot_consents").select(
            "protocol_version, privacy_version, consented_at, withdrawn_at"
        ).eq("user_id", user_id).limit(1).execute().data or []
        feedback = self.sb.table("pilot_read_feedback").select("id", count="exact").eq("user_id", user_id).execute()
        invite = self.sb.table("pilot_invitations").select("id").eq("redeemed_by", user_id).limit(1).execute().data or []
        row = consent[0] if consent else None
        return {
            **PilotPolicy.current().public(),
            "admitted": bool(row and not row.get("withdrawn_at")),
            "invitationRedeemed": bool(invite),
            "consent": row,
            "completedReads": feedback.count or 0,
        }

    def withdraw(self, user_id: str) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        rows = self.sb.table("pilot_consents").update({"withdrawn_at": now}).eq("user_id", user_id).is_(
            "withdrawn_at", "null"
        ).execute().data or []
        if not rows:
            raise ValueError("No active pilot consent")
        return {"withdrawn": True, "at": now}

    def feedback(self, user_id: str, game_id: str, resonance: str, comment: str | None) -> dict:
        game = self.sb.table("games").select("id").eq("id", game_id).eq("user_id", user_id).limit(1).execute().data or []
        if not game:
            raise ValueError("Game not found")
        row = {"user_id": user_id, "game_id": game_id, "resonance": resonance, "comment": comment or None,
               "updated_at": datetime.now(timezone.utc).isoformat()}
        return self.sb.table("pilot_read_feedback").upsert(row, on_conflict="user_id,game_id").execute().data[0]

    def exit_survey(self, user_id: str, data: dict) -> dict:
        row = {"user_id": user_id, **data}
        return self.sb.table("pilot_exit_surveys").upsert(row, on_conflict="user_id").execute().data[0]
