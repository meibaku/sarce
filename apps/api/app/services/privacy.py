"""Complete participant export and fail-closed, resumable account deletion."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from app.db.supabase import get_supabase

OWNED_TABLES = (
    "analysis_jobs",
    "brilliant_reports",
    "chaos_map",
    "drill_reviews",
    "pilot_consents",
    "pilot_exit_surveys",
    "pilot_read_feedback",
    "saved_positions",
    "shared_links",
    "traps_set",
    "user_baselines",
    "user_focus",
)


def receipt_hash(receipt: str) -> str:
    return hashlib.sha256(receipt.encode("utf-8")).hexdigest()


class PrivacyService:
    def __init__(self, client=None):
        self.sb = client or get_supabase()

    def export(self, user_id: str) -> dict:
        """Return direct and derived personal data without another participant's private rows."""
        profile = self.sb.table("profiles").select("*").eq("id", user_id).limit(1).execute().data or []
        games = self.sb.table("games").select("*").eq("user_id", user_id).execute().data or []
        game_ids = [row["id"] for row in games]
        data = {
            "schemaVersion": 1,
            "exportedAt": datetime.now(timezone.utc).isoformat(),
            "profile": profile[0] if profile else None,
            "games": games,
        }
        for table in OWNED_TABLES:
            key = "owner_user_id" if table == "scouting_reports" else "user_id"
            data[table] = self.sb.table(table).select("*").eq(key, user_id).execute().data or []
        for table in ("game_moves", "game_analyses", "game_answers", "game_ideas", "move_lens_scores"):
            data[table] = self._for_games(table, game_ids)
        data["move_annotations"] = self.sb.table("move_annotations").select("*").eq("user_id", user_id).execute().data or []
        data["style_vectors"] = self._style_vectors(user_id, game_ids)
        data["scouting_reports"] = self.sb.table("scouting_reports").select("*").eq(
            "owner_user_id", user_id
        ).execute().data or []
        return data

    def _for_games(self, table: str, game_ids: list[str]) -> list[dict]:
        if not game_ids:
            return []
        key = "game_move_id" if table == "move_lens_scores" else "game_id"
        if table == "move_lens_scores":
            move_ids = [r["id"] for r in self.sb.table("game_moves").select("id").in_("game_id", game_ids).execute().data or []]
            return self.sb.table(table).select("*").in_(key, move_ids).execute().data or [] if move_ids else []
        return self.sb.table(table).select("*").in_(key, game_ids).execute().data or []

    def _style_vectors(self, user_id: str, game_ids: list[str]) -> list[dict]:
        user_rows = self.sb.table("style_vectors").select("*").eq("entity_type", "user").eq(
            "entity_id", user_id
        ).execute().data or []
        game_rows = self.sb.table("style_vectors").select("*").eq("entity_type", "game")
        if not game_ids:
            return user_rows
        return user_rows + (game_rows.in_("entity_id", game_ids).execute().data or [])

    def start_deletion(self, user_id: str) -> dict:
        receipt = secrets.token_urlsafe(32)
        job = self.sb.table("account_deletion_jobs").insert(
            {"user_id": user_id, "receipt_hash": receipt_hash(receipt)}
        ).execute().data[0]
        try:
            steps = self._delete(user_id)
            self._job(job["id"], "complete", steps, None)
        except Exception as exc:
            self._job(job["id"], "failed", [], str(exc)[:500])
            raise RuntimeError(f"Account deletion is incomplete; retry job {job['id']}") from exc
        return {"id": job["id"], "receipt": receipt, "status": "complete"}

    def _delete(self, user_id: str) -> list[str]:
        profiles = self.sb.table("profiles").select("chess_com_username, settings").eq("id", user_id).limit(1).execute().data or []
        profile = profiles[0] if profiles else {}
        settings = profile.get("settings") or {}
        targets = {
            ("chess_com", profile.get("chess_com_username")),
            ("chess_com", settings.get("chessComUsername")),
            ("lichess", settings.get("lichessUsername")),
        }
        for source, username in targets:
            if username:
                self.sb.table("scouting_reports").delete().eq("source", source).ilike(
                    "target_username", username
                ).execute()

        games = self.sb.table("games").select("id").eq("user_id", user_id).execute().data or []
        game_ids = [row["id"] for row in games]
        self.sb.table("style_vectors").delete().eq("entity_type", "user").eq("entity_id", user_id).execute()
        if game_ids:
            self.sb.table("style_vectors").delete().eq("entity_type", "game").in_("entity_id", game_ids).execute()
        # Removing auth.users cascades through profiles, games and every owned/derived FK.
        self.sb.auth.admin.delete_user(user_id)
        return ["scouting-targets", "detached-style-vectors", "auth-user-and-cascades"]

    def _job(self, job_id: str, status: str, steps: list[str], error: str | None) -> None:
        self.sb.table("account_deletion_jobs").update({
            "status": status,
            "completed_steps": steps,
            "error": error,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", job_id).execute()

    def deletion_status(self, job_id: str, receipt: str) -> dict | None:
        rows = self.sb.table("account_deletion_jobs").select(
            "id, status, completed_steps, error, created_at, updated_at"
        ).eq("id", job_id).eq("receipt_hash", receipt_hash(receipt)).limit(1).execute().data or []
        return rows[0] if rows else None
