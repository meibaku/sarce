"""Append-only LE2 attempt contract; answers are scored server-side before persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.db.supabase import get_supabase
from app.services.patterns import CONCEPT

PROTOCOL_VERSION = 1
SCORING_VERSION = 1
PHASES = {"baseline", "learning", "immediate", "day7", "day28", "transfer"}
ASSISTANCE = {"independent", "hinted", "revealed"}


def score_response(target: dict, response: dict) -> bool:
    """Score a square selection or explicit no-danger answer without trusting a client correctness claim."""
    expected_squares = set(target.get("squares") or [])
    selected = response.get("square")
    no_danger = response.get("noImmediateDanger") is True
    if no_danger:
        return bool(target.get("noImmediateDanger")) and selected is None
    return isinstance(selected, str) and selected in expected_squares


def prepare_attempt(
    *,
    enrollment: dict,
    pattern: dict,
    client_attempt_id: str,
    phase: str,
    response: dict,
    assistance: str,
    confidence: int | None,
    latency_ms: int,
    novel: bool,
    presented_at: datetime,
    responded_at: datetime | None = None,
    scheduled_for: datetime | None = None,
) -> dict:
    """Validate the immutable evidence snapshot and derive correctness from the private pattern target."""
    if enrollment.get("withdrawn_at"):
        raise ValueError("enrollment is withdrawn")
    if phase not in PHASES or assistance not in ASSISTANCE:
        raise ValueError("invalid phase or assistance")
    if confidence is not None and confidence not in range(1, 6):
        raise ValueError("confidence must be 1 through 5")
    if not 0 <= latency_ms <= 3_600_000:
        raise ValueError("latency_ms is outside the accepted range")
    if pattern.get("review_status") != "approved" or pattern.get("concept_key") != CONCEPT:
        raise ValueError("pattern must be an approved piece-safety item")
    responded_at = responded_at or datetime.now(timezone.utc)
    if responded_at < presented_at:
        raise ValueError("response cannot precede presentation")
    # Parsing both values here rejects malformed identifiers before a database round trip.
    UUID(str(client_attempt_id))
    UUID(str(enrollment["id"]))
    return {
        "client_attempt_id": client_attempt_id,
        "enrollment_id": enrollment["id"],
        "pattern_id": pattern["id"],
        "participant_key": enrollment["participant_key"],
        "protocol_version": enrollment["protocol_version"],
        "scoring_version": SCORING_VERSION,
        "detector_version": pattern["detector_version"],
        "phase": phase,
        "arm": enrollment["arm"],
        "cohort": enrollment["cohort"],
        # Qualitative/sandbox evidence remains useful for UX review but can never enter the
        # preregistered controlled estimand. The snapshot prevents later enrollment edits
        # from rewriting an already-recorded analysis cohort.
        "analysis_eligible": (
            enrollment["cohort"] == "controlled" and enrollment.get("analysis_eligible", True) is True
        ),
        "concept_key": pattern["concept_key"],
        "family_key": pattern["family_key"],
        "item_label": pattern["label"],
        "position_key": pattern["position_key"],
        "response": response,
        "correct": score_response(pattern["target"], response),
        "assistance": assistance,
        "confidence": confidence,
        "latency_ms": latency_ms,
        "novel": novel,
        "scheduled_for": scheduled_for.isoformat() if scheduled_for else None,
        "presented_at": presented_at.isoformat(),
        "responded_at": responded_at.isoformat(),
    }


class LearningAttemptStore:
    """Durable service-role writes with idempotent retry semantics."""

    def record(self, row: dict) -> dict:
        existing = (
            get_supabase().table("learning_attempts").select("*")
            .eq("enrollment_id", row["enrollment_id"]).eq("client_attempt_id", row["client_attempt_id"])
            .limit(1).execute().data or []
        )
        if existing:
            if any(existing[0].get(key) != value for key, value in row.items()):
                raise ValueError("client_attempt_id was already used with different evidence")
            return existing[0]
        return get_supabase().table("learning_attempts").insert(row).execute().data[0]

