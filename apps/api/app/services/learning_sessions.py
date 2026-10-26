"""Fixed-manifest Learning Evidence sessions; assessment selection never adapts to answers."""

from __future__ import annotations

import hashlib
from collections import Counter
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.db.supabase import get_supabase
from app.services.learning_attempts import LearningAttemptStore, prepare_attempt
from app.services.patterns import PatternStore

PHASE_COUNTS = {"baseline": 18, "learning": 4, "immediate": 9, "day7": 18, "day28": 18}
PARTITIONS = {
    "baseline": "baseline", "learning": "instruction", "immediate": "immediate",
    "day7": "day7", "day28": "day28",
}


def label_quota(count: int) -> dict[str, int]:
    """Keep positives, near-misses and controls balanced within the fixed protocol counts."""
    if count == 4:
        return {"positive": 2, "near_miss": 1, "control": 1}
    if count % 3:
        raise ValueError("assessment count must divide evenly across labels")
    return {label: count // 3 for label in ("positive", "near_miss", "control")}


def select_patterns(patterns: list[dict], *, count: int, used_families: set[str], seed: str) -> list[dict]:
    """Build a label-balanced manifest with one item per family and no cross-phase family leakage."""
    quota = label_quota(count)
    ranked = sorted(
        patterns,
        key=lambda row: hashlib.sha256(f"{seed}|{row['id']}".encode()).hexdigest(),
    )
    selected: list[dict] = []
    families = set(used_families)
    counts: Counter[str] = Counter()
    for row in ranked:
        label, family = row.get("label"), row.get("family_key")
        if label not in quota or counts[label] >= quota[label] or family in families:
            continue
        selected.append(row)
        families.add(family)
        counts[label] += 1
    if len(selected) != count:
        raise ValueError("approved item bank cannot satisfy the fixed label and family manifest")
    return selected


class LearningSessionStore:
    """Own session manifests, answer-safe presentation, durable scoring and completion."""

    def __init__(self) -> None:
        self.patterns = PatternStore()
        self.attempts = LearningAttemptStore()

    def _enrollment(self, user_id: str) -> dict:
        rows = (
            get_supabase().table("learning_enrollments").select("*")
            .eq("user_id", user_id).limit(1).execute().data or []
        )
        if not rows or rows[0].get("withdrawn_at"):
            raise ValueError("active enrollment not found")
        return rows[0]

    def create(self, user_id: str, phase: str) -> dict:
        if phase not in PHASE_COUNTS:
            raise ValueError("invalid learning phase")
        sb = get_supabase()
        enrollment = self._enrollment(user_id)
        existing = (
            sb.table("learning_sessions").select("*").eq("enrollment_id", enrollment["id"])
            .eq("phase", phase).limit(1).execute().data or []
        )
        if existing:
            return existing[0]
        self._check_due(enrollment, phase)
        prerequisites = {"learning": "baseline", "immediate": "learning", "day7": "immediate", "day28": "day7"}
        if phase in prerequisites:
            prior = (
                sb.table("learning_sessions").select("completed_at").eq("enrollment_id", enrollment["id"])
                .eq("phase", prerequisites[phase]).limit(1).execute().data or []
            )
            if not prior or not prior[0].get("completed_at"):
                raise ValueError(f"complete {prerequisites[phase]} before starting {phase}")
        used = {
            row["family_key"] for row in (
                sb.table("learning_presentations").select("family_key")
                .eq("enrollment_id", enrollment["id"]).execute().data or []
            )
        }
        count, session_id = PHASE_COUNTS[phase], str(uuid4())
        candidates = self.patterns.approved(user_id, partition=PARTITIONS[phase], limit=500)
        selected = select_patterns(candidates, count=count, used_families=used, seed=session_id)
        created_at = datetime.now(timezone.utc).isoformat()
        session = {
            "id": session_id, "enrollment_id": enrollment["id"], "phase": phase,
            "protocol_version": enrollment["protocol_version"], "item_count": count, "created_at": created_at,
        }
        presentations = [
            {
                "id": str(uuid4()), "pattern_id": row["id"], "presentation_token": str(uuid4()),
                "ordinal": index, "family_key": row["family_key"], "item_label": row["label"],
            }
            for index, row in enumerate(selected, 1)
        ]
        sb.rpc("create_learning_session", {"p_session": session, "p_presentations": presentations}).execute()
        return session

    @staticmethod
    def _check_due(enrollment: dict, phase: str) -> None:
        enrolled = datetime.fromisoformat(enrollment["enrolled_at"].replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - enrolled.astimezone(timezone.utc)
        windows = {"day7": (6, 9), "day28": (26, 32)}
        if phase in windows and not timedelta(days=windows[phase][0]) <= age <= timedelta(days=windows[phase][1] + 1):
            raise ValueError(f"{phase} session is outside its protocol window")

    def next(self, user_id: str, session_id: str) -> dict | None:
        enrollment = self._enrollment(user_id)
        return get_supabase().rpc("next_learning_presentation", {
            "p_session_id": session_id, "p_enrollment_id": enrollment["id"],
        }).execute().data

    def answer(self, user_id: str, token: str, payload: dict) -> dict:
        sb = get_supabase()
        enrollment = self._enrollment(user_id)
        rows = (
            sb.table("learning_presentations").select("*")
            .eq("presentation_token", token).eq("enrollment_id", enrollment["id"]).limit(1).execute().data or []
        )
        if not rows or not rows[0].get("presented_at"):
            raise ValueError("presentation not found or not yet served")
        presentation = rows[0]
        if presentation.get("responded_at"):
            prior = (
                sb.table("learning_attempts").select("id")
                .eq("enrollment_id", enrollment["id"])
                .eq("client_attempt_id", payload["clientAttemptId"]).limit(1).execute().data or []
            )
            if not prior:
                raise ValueError("presentation has already been answered")
        pattern_rows = (
            sb.table("pattern_instances").select("*").eq("id", presentation["pattern_id"])
            .limit(1).execute().data or []
        )
        if not pattern_rows:
            raise ValueError("pattern not found")
        session = (
            sb.table("learning_sessions").select("phase").eq("id", presentation["session_id"])
            .limit(1).execute().data[0]
        )
        row = prepare_attempt(
            enrollment=enrollment, pattern=pattern_rows[0], client_attempt_id=payload["clientAttemptId"],
            phase=session["phase"], response=payload["response"], assistance=payload["assistance"],
            confidence=payload.get("confidence"), latency_ms=payload["latencyMs"],
            novel=True, presented_at=datetime.fromisoformat(presentation["presented_at"].replace("Z", "+00:00")),
            responded_at=(
                datetime.fromisoformat(presentation["responded_at"].replace("Z", "+00:00"))
                if presentation.get("responded_at") else None
            ),
        )
        attempt = self.attempts.record(row)  # Durable evidence crosses the boundary before acknowledgement.
        responded_at = attempt["responded_at"]
        (
            sb.table("learning_presentations").update({"responded_at": responded_at})
            .eq("id", presentation["id"]).execute()
        )
        remaining = (
            sb.table("learning_presentations").select("id", count="exact").eq("session_id", presentation["session_id"])
            .is_("responded_at", "null").limit(1).execute().count or 0
        )
        if remaining == 0:
            (
                sb.table("learning_sessions").update({"completed_at": responded_at})
                .eq("id", presentation["session_id"]).execute()
            )
        return {
            "recorded": True, "correct": attempt["correct"], "attemptId": attempt["id"], "remaining": remaining,
            "feedback": {"target": pattern_rows[0]["target"], "verification": pattern_rows[0]["verification"]},
        }

    def summary(self, user_id: str, session_id: str) -> dict:
        enrollment = self._enrollment(user_id)
        sessions = (
            get_supabase().table("learning_sessions").select("*").eq("id", session_id)
            .eq("enrollment_id", enrollment["id"]).limit(1).execute().data or []
        )
        if not sessions:
            raise ValueError("session not found")
        session = sessions[0]
        answered = (
            get_supabase().table("learning_presentations").select("id", count="exact")
            .eq("session_id", session_id).not_.is_("responded_at", "null").limit(1).execute().count or 0
        )
        return {
            "sessionId": session_id, "phase": session["phase"], "itemCount": session["item_count"],
            "answered": answered, "completedAt": session.get("completed_at"),
        }

    def progress(self, enrollment_id: str) -> list[dict]:
        """Return phase-level progress without exposing assignments, item labels or answers."""
        rows = (
            get_supabase().table("learning_sessions").select("id, phase, item_count, completed_at")
            .eq("enrollment_id", enrollment_id).order("created_at").execute().data or []
        )
        return [
            {
                "sessionId": row["id"], "phase": row["phase"], "itemCount": row["item_count"],
                "completedAt": row.get("completed_at"),
            }
            for row in rows
        ]
