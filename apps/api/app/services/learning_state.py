"""Deterministic Scheduler v2 projection rebuilt solely from immutable instruction attempts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db.supabase import get_supabase

SCHEDULER_VERSION = 2


def _instant(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("attempt timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


def next_review(attempt: dict) -> tuple[str, datetime]:
    """Apply the preregistered spacing rule; confidence can shorten but never prove learning."""
    responded = _instant(attempt["responded_at"])
    independent = attempt.get("assistance") == "independent"
    correct = attempt.get("correct") is True
    if not correct or not independent:
        return "retry", responded + timedelta(days=1)
    if attempt.get("novel") and (attempt.get("confidence") or 0) <= 2:
        return "novel", responded + timedelta(days=3)
    if attempt.get("novel"):
        return "novel", responded + timedelta(days=7)
    return "delayed", responded + timedelta(days=28)


def rebuild_state(attempts: list[dict]) -> list[dict]:
    """Fold instruction attempts into one reproducible row per participant, concept and family."""
    state: dict[tuple[str, str, str], dict] = {}
    ordered = sorted(
        (row for row in attempts if row.get("phase") == "learning"),
        key=lambda row: (_instant(row["responded_at"]), str(row["id"])),
    )
    for row in ordered:
        key = (str(row["enrollment_id"]), row["concept_key"], row["family_key"])
        stage, due_at = next_review(row)
        prior = state.get(key)
        independent_correct = (prior or {}).get("independent_correct", 0)
        if row.get("correct") is True and row.get("assistance") == "independent":
            independent_correct += 1
        state[key] = {
            "enrollment_id": row["enrollment_id"],
            "participant_key": row["participant_key"],
            "concept_key": row["concept_key"],
            "family_key": row["family_key"],
            "scheduler_version": SCHEDULER_VERSION,
            "stage": stage,
            "due_at": due_at.isoformat(),
            "last_attempt_id": row["id"],
            "independent_correct": independent_correct,
            "updated_at": _instant(row["responded_at"]).isoformat(),
        }
    return sorted(state.values(), key=lambda row: (row["due_at"], row["family_key"]))


class LearningStateStore:
    """Replace the disposable projection for one enrolment after deriving it in memory."""

    def rebuild(self, enrollment_id: str) -> list[dict]:
        sb = get_supabase()
        attempts = (
            sb.table("learning_attempts").select("*").eq("enrollment_id", enrollment_id)
            .order("responded_at").execute().data or []
        )
        rows = rebuild_state(attempts)
        sb.table("learning_state").delete().eq("enrollment_id", enrollment_id).execute()
        if rows:
            sb.table("learning_state").insert(rows).execute()
        return rows

