"""
The full Brilliant rule (v4, ADR 0009) applied to a stored game, from stored data only.

Every one of your moves is judged again from scratch: the board clauses (real offer, sound, not lost, not already
winning, not forced) from the stored evaluations and engine lines, then the find-rate clause (ADR 0004) at your own
rating converted to the model's scale (nearest 100; review F1/F11a), read from the `human_probs` cache or computed
on a miss. Moves can be promoted as well as demoted, so a rule change reaches past games. The distribution,
Brilliant % and style vector are recomputed and the vector is marked with VERSION / RULE.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.db.supabase import get_supabase
from app.services.baseline import BaselineService
from app.services.brilliant import (
    BOARD_CLAUSES,
    alternatives_from_row,
    best_eval_from_row,
    brilliant_clauses,
    hard_to_find,
)
from app.services.human_model import ELO_LADDER, SupabaseProbStore, cached_move_probs, get_human_model
from app.services.library import boards_before
from app.services.rating_map import opponent_model_elo, user_model_elo

logger = logging.getLogger(__name__)

RULE = "v4"  # ADR 0009: sound / not lost / not forced in expected points, find-rate at your rating, real offer
VERSION = 5  # 5: rule v4 (ADR 0009); 4: find-rate at your converted rating (F1/F11a); 3: real offer (ADR 0007)


def mover_rung(game: dict) -> int:
    """
    The rating the find-rate clause is judged at: your own rating in that game on the model's scale, to the nearest
    100 (finding a move is about the mover). Falls back to the opponent's converted rating, then 1600.
    """
    elo = user_model_elo(game) or opponent_model_elo(game)
    return int(round(elo / 100.0)) * 100 if elo else 1600


def rung_for(opponent_rating: int | None) -> int:
    """The ladder rating nearest the opponent's, the proxy the lenses use for the player's level."""
    if not opponent_rating:
        return 1600
    return min(ELO_LADDER, key=lambda r: abs(r - opponent_rating))


def rejudge(moves: list[dict], boards: list, probs_for) -> tuple[list[dict], int]:
    """
    Judge stored moves again under the full rule. `boards[ply]` is (board before, move); `probs_for(ply)` returns
    the human-model probabilities before that move or None (asked only for moves that pass the board clauses).
    A move that stops being Brilliant gets its quality back from its centipawn loss. Returns (moves, changed).
    """
    from app.services.move_classifier import classify_move_quality

    out, changed = [], 0
    for m in moves:
        brilliant = False
        if m["ply"] < len(boards) and m.get("eval_before") is not None and m.get("eval_after") is not None:
            board, move = boards[m["ply"]]
            clauses = brilliant_clauses(
                board, move, m["eval_before"], m["eval_after"], best_eval_from_row(m), alternatives=alternatives_from_row(m)
            )
            if all(clauses[c] for c in BOARD_CLAUSES):
                # No human-model data keeps the move Brilliant, as the find-rate rule always has.
                brilliant = hard_to_find(probs_for(m["ply"]), m.get("uci") or "") is not False
        quality = m.get("quality")
        if brilliant:
            quality = "brilliant"
        elif quality == "brilliant":
            quality = classify_move_quality(float(m.get("cp_loss") or 0), m.get("eval_before"), m.get("eval_after")).value
        if brilliant != bool(m.get("is_brilliant")) or quality != m.get("quality"):
            changed += 1
            m = {**m, "is_brilliant": brilliant, "quality": quality}
        out.append(m)
    return out, changed


def apply_rule(moves: list[dict], probs_for, offered_for=lambda m: None) -> tuple[list[dict], int]:
    """
    Re-classify Brilliant moves that are easy to find. `probs_for(ply)` returns the human-model
    probabilities before that move, or None. Returns (updated moves, number demoted). Moves with no
    human-model data keep their classification.
    """
    demoted = 0
    out = []
    for m in moves:
        if m.get("is_brilliant"):
            verdict = hard_to_find(probs_for(m["ply"]), m.get("uci") or "")
            if verdict is False or offered_for(m) is False:
                m = {**m, "is_brilliant": False, "quality": "best"}
                demoted += 1
        out.append(m)
    return out, demoted


def style_vector_v2(previous: dict | None, distribution: dict, brilliant_pct: float) -> dict:
    """The stored vector with the new rule's numbers and version (ADR 0004)."""
    return {**(previous or {}), "version": VERSION, "brilliantRule": RULE, "brilliantPct": round(brilliant_pct, 2), "distribution": distribution}


class BrilliantFindRate:
    def apply(self, game_id: str) -> dict | None:
        """Applies the rule to one game; returns a summary, or None when the game is missing."""
        sb = get_supabase()
        rows = sb.table("games").select("id, pgn, opponent_rating, user_rating, source, time_control").eq("id", game_id).limit(1).execute().data
        if not rows:
            return None
        game = rows[0]
        moves = (
            sb.table("game_moves").select("id, ply, uci, quality, is_brilliant, cp_loss, eval_before, eval_after, best_uci, pv")
            .eq("game_id", game_id).order("ply").execute().data
            or []
        )
        analysis = (sb.table("game_analyses").select("style_vector").eq("game_id", game_id).limit(1).execute().data or [{}])[0]
        plies = boards_before(game.get("pgn") or "")
        model, store = get_human_model(settings.human_model), SupabaseProbStore()
        elo = mover_rung(game)

        def probs_for(ply: int):
            if ply >= len(plies):
                return None
            try:
                return cached_move_probs(plies[ply][0], elo, model, store)
            except Exception:
                logger.exception("Human-model probabilities failed for %s ply %s", game_id, ply)
                return None

        updated, changed = rejudge(moves, plies, probs_for)
        for before, after in zip(moves, updated):
            if before != after:
                sb.table("game_moves").update({"is_brilliant": after["is_brilliant"], "quality": after["quality"]}).eq("id", after["id"]).execute()

        distribution = BaselineService.compute_distribution([m["quality"] for m in updated])
        pct = BaselineService.brilliant_pct(distribution)
        sb.table("game_analyses").update(
            {"distribution": distribution, "brilliant_pct": pct, "style_vector": style_vector_v2(analysis.get("style_vector"), distribution, pct)}
        ).eq("game_id", game_id).execute()
        return {"gameId": game_id, "changed": changed, "brilliantPct": pct, "elo": elo, "model": model.model_version}
