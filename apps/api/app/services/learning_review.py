"""Independent, blinded item-bank review for the Learning Evidence pilot."""

from __future__ import annotations

from app.db.supabase import get_supabase
from app.services.pattern_review import review_report
from app.services.patterns import CONCEPT, PatternStore, TABLE


def reviewer_view(row: dict) -> dict:
    """Expose evidence needed to judge one candidate, never another reviewer's vote."""
    return {
        "id": row["id"],
        "positionFen": row["position_fen"],
        "proposedLabel": row["label"],
        "target": row["target"],
        "verification": row["verification"],
        "familyKey": row["family_key"],
        "detectorVersion": row["detector_version"],
        "stockfishVersion": row["stockfish_version"],
        "analysisNodes": row["analysis_nodes"],
    }


class LearningReviewStore:
    """Serve independent work, record one immutable vote per reviewer, and report gates."""

    def __init__(self) -> None:
        self.patterns = PatternStore()

    def next(self, reviewer_id: str) -> dict | None:
        rows = (
            get_supabase().table(TABLE).select("*").eq("concept_key", CONCEPT)
            .eq("review_set", "heldout").eq("review_status", "candidate")
            .order("created_at").limit(500).execute().data or []
        )
        for row in rows:
            votes = row.get("review_annotations") or []
            if not any(vote.get("reviewer") == reviewer_id for vote in votes):
                return reviewer_view(row)
        return None

    def annotate(self, pattern_id: str, reviewer_id: str, decision: str, note: str) -> dict:
        self.patterns.annotate(pattern_id, reviewer_id, decision, note)
        return {"recorded": True, "patternId": pattern_id}

    def metrics(self) -> dict:
        rows = (
            get_supabase().table(TABLE).select("review_set, review_status, review_annotations")
            .eq("concept_key", CONCEPT).eq("review_set", "heldout").limit(5000).execute().data or []
        )
        return review_report(rows)

    def adjudicate(self, pattern_id: str, status: str) -> dict:
        row = self.patterns.set_status(pattern_id, status)
        return {"patternId": row["id"], "status": row["review_status"]}
