"""
Game analysis orchestration — classify, persist, update baseline.

Phase 1 pipeline: pending game → Stockfish → game_moves + game_analyses → baseline.
"""

from __future__ import annotations

import asyncio
import io
import logging

import chess
import chess.pgn

from app.config import settings
from app.db.supabase import get_supabase
from app.services.baseline import BaselineService, EMPTY_DISTRIBUTION
from app.services.human_model import (
    SupabaseProbStore,
    cached_move_probs,
    elo_ladder,
    get_human_model,
)
from app.services.lens_service import LensService
from app.services.move_classifier import MoveClassifier
from app.services.move_signals import signal_distribution
from app.services.pgn_parser import extract_clocks_ms
from app.services.position_evals import (
    SupabaseEvalStore,
    evaluate_game_positions,
    iter_live_positions,
)
from app.services.stockfish import StockfishEngine

logger = logging.getLogger(__name__)


def build_style_vector_v1(
    distribution: dict,
    brilliant_pct: float,
    classified_moves: list[dict] | None = None,
) -> dict:
    """
    Versioned style vector schema (v1).

    Evolves in Phase 2+ as similarity features are added.
    """
    classified_moves = classified_moves or []
    total = sum(distribution.values()) or 1
    signals = signal_distribution(classified_moves)
    sacrifice_moves = (
        sum(
            1
            for move in classified_moves
            if any(
                signal in move.get("signals", [])
                for signal in (
                    "sacrifice",
                    "exchange_sacrifice",
                    "breakthrough_sacrifice",
                    "brilliant_sacrifice",
                )
            )
        )
        if classified_moves
        else distribution.get("brilliant", 0)
    )
    tactical_moves = sum(
        1
        for move in classified_moves
        if any(
            signal in move.get("signals", [])
            for signal in (
                "tactical_resource",
                "momentum_shift",
                "evaluation_swing",
                "breakthrough_sacrifice",
            )
        )
    )
    eval_swings = [
        abs(move["eval_after"] - move["eval_before"])
        for move in classified_moves
        if move.get("eval_after") is not None and move.get("eval_before") is not None
    ]
    return {
        "version": 1,
        "brilliantPct": round(brilliant_pct, 2),
        "sacrificeRate": round(sacrifice_moves / total, 4),
        "tacticalComplexity": round(tactical_moves / total, 4),
        "evalVolatility": round(sum(eval_swings) / len(eval_swings), 3)
        if eval_swings
        else 0.0,
        "distribution": distribution,
        "signalDistribution": signals,
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
                "san": m.get("san"),
                "quality": m["quality"],
                "cp_loss": m["cp_loss"],
                "eval_before": m["eval_before"],
                "eval_after": m["eval_after"],
                "is_brilliant": m["is_brilliant"],
                "phase": m.get("phase"),
                "signals": m.get("signals", []),
                "highlight": m.get("highlight"),
                "best_uci": m.get("best_uci"),
                "best_san": m.get("best_san"),
                "pv": m.get("pv", []),
            }
            for m in classified
        ]
        if move_rows:
            sb.table("game_moves").insert(move_rows).execute()

        qualities = [m["quality"] for m in classified]
        distribution = BaselineService.compute_distribution(qualities)
        brilliant_pct = BaselineService.brilliant_pct(distribution)
        style_vector = build_style_vector_v1(distribution, brilliant_pct, classified)

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

        # After everything Phase 1 has been saved, so the extra engine time cannot delay it.
        # In a worker thread: the engine searches would otherwise block the API event loop.
        if settings.position_evals_enabled:
            await asyncio.to_thread(
                self._store_chaos_raw_data,
                game_id, row["pgn"], board, moves, user_color, classified,
                row.get("opponent_rating"),
            )

        return {
            "gameId": game_id,
            "brilliantPct": brilliant_pct,
            "totalMoves": len(classified),
            "distribution": distribution,
        }

    def _store_chaos_raw_data(
        self,
        game_id: str,
        pgn_text: str,
        board: chess.Board,
        moves: list[chess.Move],
        user_color: str,
        classified: list[dict],
        opponent_rating: int | None = None,
    ) -> None:
        """
        Chaos Lens raw data: per-ply clocks, cached position evaluations and human
        move probabilities at each ladder Elo.

        Runs after Phase 1 results are saved and never fails the analysis — a problem
        here is logged and the game stays `complete` (docs/CHAOS_PLAN.md, rule 1).
        The outcome is recorded in `games.chaos_data_status` so failed games can be
        found and backfilled instead of silently missing lens data.
        """
        games = get_supabase().table("games")
        try:
            games.update({"clocks_ms": extract_clocks_ms(pgn_text)}).eq("id", game_id).execute()
            with StockfishEngine() as engine:
                stats = evaluate_game_positions(
                    board, moves, user_color, classified, engine, SupabaseEvalStore()
                )
            model, prob_store = get_human_model(settings.human_model), SupabaseProbStore()
            elos = elo_ladder(opponent_rating)
            for _ply, position in iter_live_positions(board, moves, user_color, classified):
                for elo in elos:
                    cached_move_probs(position, elo, model, prob_store)
            # Lenses read only what was just stored; no further engine work.
            LensService().score_game(game_id)
            logger.info("Position evals for game %s: %s", game_id, stats)
            status = "failed" if stats["failed"] else "complete"
        except Exception:
            logger.exception("Chaos raw-data pass failed for game %s", game_id)
            status = "failed"
        try:
            games.update({"chaos_data_status": status}).eq("id", game_id).execute()
        except Exception:
            logger.exception("Could not record chaos data status for game %s", game_id)

    async def backfill_chaos_data(self, limit: int = 20, username: str | None = None) -> dict:
        """
        Run the raw-data pass for analysed games that have no chaos data yet (or failed).

        For games analysed before the Chaos Lens existed, or while it was switched off.
        Phase 1 results are read back from `game_moves`; nothing in Phase 1 is recomputed.
        """
        sb = get_supabase()
        query = (
            sb.table("games")
            .select("id, pgn, user_color, opponent_rating, chaos_data_status")
            .eq("analysis_status", "complete")
            .or_("chaos_data_status.is.null,chaos_data_status.eq.failed")
            .limit(limit)
        )
        if username:
            query = query.eq("chess_com_username", username)
        done = {"attempted": 0, "skipped": 0}
        for game in query.execute().data or []:
            parsed = self._parse_game(game["pgn"])
            moves_res = (
                sb.table("game_moves")
                .select("ply, eval_before, eval_after")
                .eq("game_id", game["id"])
                .execute()
            )
            if not parsed or not moves_res.data:
                done["skipped"] += 1
                continue
            board, moves = parsed
            await asyncio.to_thread(
                self._store_chaos_raw_data,
                game["id"], game["pgn"], board, moves,
                game.get("user_color") or "white", moves_res.data, game.get("opponent_rating"),
            )
            done["attempted"] += 1
        return done

    async def analyze_pending(
        self,
        user_id: str | None = None,
        chess_com_username: str | None = None,
        limit: int | None = None,
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
        )
        if limit is not None:
            query = query.limit(limit)
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
