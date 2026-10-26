"""LE2 reviewed pattern bank: explicit scope, immutable provenance and answer-safe serving views."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import chess

from app.db.supabase import get_supabase
from app.services.position_evals import fen_key

TABLE = "pattern_instances"
CONCEPT = "piece_safety.hanging_piece"
VISIBILITIES = {"private", "global"}
SOURCES = {"own_game", "curated", "generated"}
LABELS = {"positive", "near_miss", "control"}
PARTITIONS = {"baseline", "instruction", "immediate", "day7", "day28", "transfer"}
PUBLIC_FIELDS = {
    "id", "concept_key", "position_fen", "family_key", "source_type", "source_game_id", "source_ply", "label",
    "difficulty_context", "bank_partition", "detector_version",
}


def _choice(value: str, allowed: set[str], name: str) -> str:
    if value not in allowed:
        raise ValueError(f"{name} must be one of {sorted(allowed)}")
    return value


def prepare_candidate(
    *,
    fen: str,
    family_key: str,
    visibility: str,
    owner_id: str | None,
    source_type: str,
    source_game_id: str | None,
    source_ply: int | None,
    label: str,
    target: dict,
    verification: dict,
    stockfish_version: str,
    analysis_nodes: int,
    detector_version: int,
    difficulty_context: dict | None = None,
    bank_partition: str | None = None,
    concept_key: str = CONCEPT,
) -> dict:
    """Validate and normalize a detector candidate before any durable write."""
    board = chess.Board(fen)
    if not board.is_valid() or board.is_game_over():
        raise ValueError("pattern must be a playable position")
    visibility = _choice(visibility, VISIBILITIES, "visibility")
    source_type = _choice(source_type, SOURCES, "source_type")
    label = _choice(label, LABELS, "label")
    if bank_partition is not None:
        _choice(bank_partition, PARTITIONS, "bank_partition")
    if visibility == "private" and not owner_id:
        raise ValueError("private patterns require owner_id")
    if visibility == "global" and owner_id is not None:
        raise ValueError("global patterns cannot have owner_id")
    if source_type == "own_game" and (visibility != "private" or not source_game_id):
        raise ValueError("own-game patterns must be private and name their game")
    if source_type != "own_game" and source_game_id is not None:
        raise ValueError("only own-game patterns can name a source game")
    if source_ply is not None and source_ply < 0:
        raise ValueError("source_ply must be non-negative")
    if analysis_nodes <= 0 or detector_version <= 0:
        raise ValueError("analysis_nodes and detector_version must be positive")
    family_key = family_key.strip()
    if not family_key:
        raise ValueError("family_key is required")
    normalized = board.fen()
    key = fen_key(board)
    scope = owner_id if visibility == "private" else "global"
    dedupe = hashlib.sha256(f"{scope}|{concept_key}|{key}|{detector_version}".encode()).hexdigest()
    return {
        "owner_id": owner_id,
        "visibility": visibility,
        "concept_key": concept_key,
        "position_fen": normalized,
        "position_key": key,
        "family_key": family_key[:200],
        "dedupe_key": dedupe,
        "source_type": source_type,
        "source_game_id": source_game_id,
        "source_ply": source_ply,
        "label": label,
        "target": target,
        "verification": verification,
        "difficulty_context": difficulty_context or {},
        "bank_partition": bank_partition,
        "stockfish_version": stockfish_version[:100],
        "analysis_nodes": analysis_nodes,
        "detector_version": detector_version,
        "review_status": "candidate",
        "review_annotations": [],
        "annotation_count": 0,
    }


def serving_view(row: dict) -> dict:
    """The only pattern shape suitable for a client before it submits a response."""
    return {key: row.get(key) for key in PUBLIC_FIELDS if key in row}


class PatternStore:
    def put_candidate(self, row: dict) -> dict:
        """Create or refresh a candidate; an approved/rejected item is never silently reinterpreted."""
        existing = get_supabase().table(TABLE).select("*").eq("dedupe_key", row["dedupe_key"]).limit(1).execute().data or []
        if existing and existing[0].get("review_status") != "candidate":
            return existing[0]
        return get_supabase().table(TABLE).upsert(row, on_conflict="dedupe_key").execute().data[0]

    def approved(self, owner_id: str, concept_key: str = CONCEPT, partition: str | None = None, limit: int = 100) -> list[dict]:
        """Approved personal rows plus explicitly global rows; callers still sanitize before serving."""
        query = (
            get_supabase().table(TABLE).select("*").eq("concept_key", concept_key).eq("review_status", "approved")
            .or_(f"owner_id.eq.{owner_id},visibility.eq.global").order("created_at").limit(min(max(limit, 1), 500))
        )
        if partition is not None:
            _choice(partition, PARTITIONS, "partition")
            query = query.eq("bank_partition", partition)
        return query.execute().data or []

    def annotate(self, pattern_id: str, reviewer: str, decision: str, note: str = "") -> dict:
        """Append one independent review; the same reviewer cannot overwrite or vote twice."""
        decision = _choice(decision, {"approve", "reject", "unclear"}, "decision")
        rows = get_supabase().table(TABLE).select("*").eq("id", pattern_id).limit(1).execute().data or []
        if not rows:
            raise ValueError("pattern not found")
        row = rows[0]
        annotations = list(row.get("review_annotations") or [])
        reviewer = reviewer.strip()[:80]
        if not reviewer:
            raise ValueError("reviewer is required")
        if any(item.get("reviewer") == reviewer for item in annotations):
            raise ValueError("reviewer already annotated this pattern")
        annotations.append({
            "reviewer": reviewer,
            "decision": decision,
            "note": note.strip()[:500],
            "at": datetime.now(timezone.utc).isoformat(),
        })
        payload = {"review_annotations": annotations, "annotation_count": len(annotations), "updated_at": datetime.now(timezone.utc).isoformat()}
        return get_supabase().table(TABLE).update(payload).eq("id", pattern_id).eq("review_status", "candidate").execute().data[0]

    def set_status(self, pattern_id: str, status: str) -> dict:
        """Reviewer-only adjudication after two independent votes; disagreements remain in the audit trail."""
        status = _choice(status, {"approved", "rejected", "retired"}, "status")
        rows = get_supabase().table(TABLE).select("*").eq("id", pattern_id).limit(1).execute().data or []
        if not rows:
            raise ValueError("pattern not found")
        annotations = rows[0].get("review_annotations") or []
        decisions = {item.get("decision") for item in annotations}
        if status in {"approved", "rejected"} and len(annotations) < 2:
            raise ValueError("adjudication requires two independent annotations")
        if status == "approved" and "approve" not in decisions:
            raise ValueError("approval requires an affirmative annotation")
        if status == "rejected" and "reject" not in decisions:
            raise ValueError("rejection requires a rejecting annotation")
        payload = {"review_status": status, "updated_at": datetime.now(timezone.utc).isoformat()}
        return get_supabase().table(TABLE).update(payload).eq("id", pattern_id).execute().data[0]
