"""
The Brilliant find-rate rule (ADR 0004) applied to a stored game.

For every move classified Brilliant, the human model's probability of the played move at your own rating
(converted to the model's scale, nearest 100; review F1/F11a) is read (from the `human_probs` cache, computing it on a miss). Moves
found more than FIND_RATE_MAX of the time become "best"; the distribution, Brilliant % and style
vector are recomputed and the vector is marked version 2 / "find-rate-20".
"""

from __future__ import annotations

import logging

from app.config import settings
from app.db.supabase import get_supabase
from app.services.baseline import BaselineService
from app.services.brilliant import MIN_BRILLIANT_SACRIFICE_VALUE, hard_to_find, real_offer
from app.services.human_model import ELO_LADDER, SupabaseProbStore, cached_move_probs, get_human_model
from app.services.library import boards_before
from app.services.rating_map import opponent_model_elo, user_model_elo

logger = logging.getLogger(__name__)

RULE = "find-rate-20@mover+real-offer"
VERSION = 4  # 4: found by ≤20% of players at *your* converted rating (review F1/F11a); 3: real offer (ADR 0007)


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
        moves = sb.table("game_moves").select("id, ply, uci, quality, is_brilliant").eq("game_id", game_id).order("ply").execute().data or []
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

        def offered_for(m: dict):
            """False when the 'sacrificed' piece was never really on offer (ADR 0007)."""
            if m["ply"] >= len(plies):
                return None
            board, move = plies[m["ply"]]
            return real_offer(board, move) >= MIN_BRILLIANT_SACRIFICE_VALUE

        updated, demoted = apply_rule(moves, probs_for, offered_for)
        for before, after in zip(moves, updated):
            if before != after:
                sb.table("game_moves").update({"is_brilliant": False, "quality": "best"}).eq("id", after["id"]).execute()

        distribution = BaselineService.compute_distribution([m["quality"] for m in updated])
        pct = BaselineService.brilliant_pct(distribution)
        sb.table("game_analyses").update(
            {"distribution": distribution, "brilliant_pct": pct, "style_vector": style_vector_v2(analysis.get("style_vector"), distribution, pct)}
        ).eq("game_id", game_id).execute()
        return {"gameId": game_id, "demoted": demoted, "brilliantPct": pct, "elo": elo, "model": model.model_version}
