"""
Game analysis orchestration — classify, persist, update baseline.

Phase 1 pipeline: pending game → Stockfish → game_moves + game_analyses → baseline.
"""

from __future__ import annotations

import io
import logging

import chess
import chess.pgn

from app.db.supabase import get_supabase
from app.services.baseline import BaselineService, EMPTY_DISTRIBUTION
from app.services.move_classifier import MoveClassifier

logger = logging.getLogger(__name__)


def build_style_vector_v1(distribution: dict, brilliant_pct: float) -> dict:
    """
    Versioned style vector schema (v1).

    Evolves in Phase 2+ as similarity features are added.
    """
    total = sum(distribution.values()) or 1
    sacrifices = distribution.get("brilliant", 0)
    return {
        "version": 1,
        "brilliantPct": round(brilliant_pct, 2),
        "sacrificeRate": round(sacrifices / total, 4),
        "tacticalComplexity": 0.0,
        "evalVolatility": 0.0,
        "distribution": distribution,
    }


class AnalysisService:
    """Run Stockfish classification and persist results."""

    def __init__(self) -> None:
        self.classifier = MoveClassifier()
        self.baseline = BaselineService()

    def _parse_game(self, pgn_text: str) -> tuple[chess.Board, list[chess.Move]] | None:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
        if game is None:
            return None
        board = game.board()
        moves = list(game.mainline_moves())
        return board, moves

    async def analyze_game(self, game_id: str) -> dict | None:
        """
        Analyze a single game by ID.

        Returns summary dict or None if game not found / parse failed.
        """
        sb = get_supabase()
        res = sb.table("games").select("*").eq("id", game_id).maybe_single().execute()
        if not res.data:
            return None

        row = res.data
        user_color = row.get("user_color") or "white"
        parsed = self._parse_game(row["pgn"])
        if not parsed:
            sb.table("games").update({"analysis_status": "failed"}).eq("id", game_id).execute()
            return None

        board, moves = parsed
        sb.table("games").update({"analysis_status": "processing"}).eq("id", game_id).execute()

        try:
            classified = self.classifier.classify_game(board, moves, user_color)
        except Exception as exc:
            logger.exception("Analysis failed for game %s: %s", game_id, exc)
            sb.table("games").update({"analysis_status": "failed"}).eq("id", game_id).execute()
            raise

        # Clear prior moves if re-analyzing
        sb.table("game_moves").delete().eq("game_id", game_id).execute()

        move_rows = [
            {
                "game_id": game_id,
                "ply": m["ply"],
                "uci": m["uci"],
                "quality": m["quality"],
                "cp_loss": m["cp_loss"],
                "eval_before": m["eval_before"],
                "eval_after": m["eval_after"],
                "is_brilliant": m["is_brilliant"],
            }
            for m in classified
        ]
        if move_rows:
            sb.table("game_moves").insert(move_rows).execute()

        qualities = [m["quality"] for m in classified]
        distribution = BaselineService.compute_distribution(qualities)
        brilliant_pct = BaselineService.brilliant_pct(distribution)
        style_vector = build_style_vector_v1(distribution, brilliant_pct)

        sb.table("game_analyses").upsert(
            {
                "game_id": game_id,
                "distribution": distribution,
                "brilliant_pct": brilliant_pct,
                "total_moves": len(classified),
                "style_vector": style_vector,
            },
            on_conflict="game_id",
        ).execute()

        sb.table("games").update({"analysis_status": "complete"}).eq("id", game_id).execute()

        await self.baseline.recompute_baseline(
            user_id=row.get("user_id"),
            chess_com_username=row.get("chess_com_username"),
        )

        return {
            "gameId": game_id,
            "brilliantPct": brilliant_pct,
            "totalMoves": len(classified),
            "distribution": distribution,
        }

    async def analyze_pending(
        self,
        user_id: str | None = None,
        chess_com_username: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """
        Analyze up to `limit` games with status 'pending'.

        Filters by user_id and/or chess_com_username when provided.
        """
        sb = get_supabase()
        query = (
            sb.table("games")
            .select("id")
            .eq("analysis_status", "pending")
            .limit(limit)
        )
        if user_id:
            query = query.eq("user_id", user_id)
        if chess_com_username:
            query = query.eq("chess_com_username", chess_com_username)

        res = query.execute()
        results = []
        for row in res.data or []:
            summary = await self.analyze_game(row["id"])
            if summary:
                results.append(summary)
        return results
