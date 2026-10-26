"""
Game analysis orchestration — classify, persist, update baseline.

Phase 1 pipeline: pending game → Stockfish → game_moves + game_analyses → baseline.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
import io
import logging
import re

import chess
import chess.pgn

from app.config import settings
from app.db.supabase import get_supabase
from app.services import monitor
from app.services.baseline import BaselineService, EMPTY_DISTRIBUTION
from app.services.brilliant_find_rate import BrilliantFindRate
from app.services.rating_map import opponent_model_elo
from app.services.human_model import (
    SupabaseProbStore,
    cached_move_probs,
    elo_ladder,
    get_human_model_for_game,
)
from app.services.lens_service import LensService
from app.services.move_classifier import MoveClassifier
from app.services.move_signals import signal_distribution
from app.services.pgn_parser import extract_clocks_ms
from app.services.threats import SupabaseThreatStore, evaluate_game_threats
from app.services.position_evals import (
    SupabaseEvalStore,
    evaluate_game_positions,
    game_lines,
    iter_live_positions,
)
from app.services.stockfish import StockfishEngine
from app.services.tagger import TaggerService

logger = logging.getLogger(__name__)

TRANSIENT_DB_CODES = {"57014", "40001", "40P01", "53300", "08006"}  # statement timeout, serialization, deadlock, too many connections, connection lost


MAX_ATTEMPTS = 3
MAX_ERROR_LENGTH = 500
_SECRET = re.compile(
    r'''(?ix)(?P<prefix>bearer\s+|["']?(?:api[_-]?key|token|password|secret)["']?\s*[=:]\s*)'''
    r'''(?:"[^"]*"|'[^']*'|[^\s,}\]]+)'''
)


def is_transient(exc: BaseException) -> bool:
    """Worth retrying later: a database timeout, a dropped connection, or the engine timing out or dying under load."""
    import chess.engine
    import httpx

    if isinstance(exc, (httpx.TransportError, TimeoutError, ConnectionError, chess.engine.EngineTerminatedError)):
        return True
    code = getattr(exc, "code", None)
    return code in TRANSIENT_DB_CODES or any(c in str(exc) for c in TRANSIENT_DB_CODES)


def safe_failure(exc: BaseException) -> tuple[str, str]:
    """Return bounded operator diagnostics without persisting credentials or multiline payloads."""
    error_type = type(exc).__name__[:80]
    message = " ".join(str(exc).split())
    message = _SECRET.sub(lambda match: f"{match.group('prefix')}[redacted]", message)
    return error_type, message[:MAX_ERROR_LENGTH]


def _monitor_failure(slot: int | None, game_id: str, detail: dict) -> None:
    """Bridge structured failure detail through the monitor's positional background runner."""
    monitor.event("game_failed", monitor.MACHINE, slot, game_id, **detail)


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
        self._first_read_done: set[str] = set()
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

        Returns summary dict or None if game not found / parse failed. Reported to the analysis monitor: the slot is
        busy with this game, and the game's end (finished, failed, or finished from a node's search) is an event.
        """
        started = time.monotonic()
        claim = {"ours": False}  # set once this call has flipped the game to 'processing'
        with monitor.track_game(game_id) as tracker:
            try:
                result = await self._analyze_game(game_id, claim)
            except Exception as exc:
                # Only the call that claimed the game may hand it back: a caller that failed before claiming (a
                # database timeout reading the row) would otherwise requeue a game another worker is analysing,
                # and it would be analysed twice.
                detail = claim.get("failure")
                if claim["ours"]:
                    detail = self._release(game_id, exc)
                monitor.background(_monitor_failure, tracker.slot, game_id, detail or {})
                logger.debug("monitor: game %s failed: %s", game_id, exc)
                raise
        if result:
            # Positions searched or looked up, the same measure nodes report; off the event loop.
            monitor.background(
                monitor.game_finished, game_id, round(time.monotonic() - started), len(tracker.seen) or tracker.done,
                result.get("totalMoves"), tracker.slot,
            )
        return result

    async def _analyze_game(self, game_id: str, claim: dict | None = None) -> dict | None:
        sb = get_supabase()
        res = sb.table("games").select("*").eq("id", game_id).maybe_single().execute()
        if not res or not res.data:
            return None

        row = res.data
        user_color = row.get("user_color") or "white"
        parsed = self._parse_game(row["pgn"])
        if not parsed:
            self._record_failure(game_id, row, ValueError("PGN could not be parsed"), retryable=False)
            return None

        board, moves = parsed
        if row.get("analysis_status") == "pending":
            # Claim it atomically: the queue and the node-finisher can reach the same pending game at once, and two
            # analyses of one game collide on its lens rows. Whoever flips pending -> processing first does it.
            claimed = sb.table("games").update({"analysis_status": "processing"}).eq("id", game_id).eq("analysis_status", "pending").execute()
            if not claimed.data:
                return None
            if claim is not None:
                claim["ours"] = True
        elif row.get("analysis_status") == "processing":
            return None  # someone is on it (a crash's leftovers go back to pending at startup)
        else:
            # Reanalysis of a finished or failed game: claimed the same way, from the status it was read with.
            claimed = (
                sb.table("games").update({"analysis_status": "processing"}).eq("id", game_id)
                .eq("analysis_status", row.get("analysis_status")).execute()
            )
            if not claimed.data:
                return None
            if claim is not None:
                claim["ours"] = True
        # A different worker may have claimed and failed this row between our initial read and our successful
        # conditional claim. Re-read the durable budget only after ownership is established so failures cannot
        # overwrite a newer attempt count with the stale pre-claim value.
        attempts = sb.table("games").select("analysis_attempts").eq("id", game_id).maybe_single().execute()
        if attempts and attempts.data:
            row["analysis_attempts"] = attempts.data.get("analysis_attempts", row.get("analysis_attempts", 0))
        tracker = monitor.current.get()
        if tracker:
            tracker.phase("searching", total=len(moves) + 1)

        try:
            # In a worker thread (it opens its own engine): searching on the event loop froze the API.
            classified = await asyncio.to_thread(self._classify, board, moves, user_color)
        except Exception as exc:
            logger.exception("Analysis failed for game %s: %s", game_id, exc)
            # Attempts live on the game, not in this process, so restarts cannot reset the retry budget.
            detail = self._record_failure(game_id, row, exc)
            if claim is not None:
                claim["failure"] = detail
                claim["ours"] = False  # settled here: nothing left to hand back
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

        sb.table("games").update({
            "analysis_status": "complete",
            "analysed_at": datetime.now(timezone.utc).isoformat(),
            "analysis_attempts": 0,
            "analysis_error": None,
            "analysis_failed_at": None,
        }).eq("id", game_id).execute()
        self._first_read(row.get("user_id"))

        await self.baseline.recompute_baseline(
            user_id=row.get("user_id"),
            chess_com_username=row.get("chess_com_username"),
        )

        if settings.idea_tagger_enabled:
            await asyncio.to_thread(self._tag_ideas, game_id)

        # After everything Phase 1 has been saved, so the extra engine time cannot delay it.
        # In a worker thread: the engine searches would otherwise block the API event loop.
        if settings.position_evals_enabled:
            await asyncio.to_thread(
                self._store_chaos_raw_data,
                game_id, row["pgn"], board, moves, user_color, classified,
                opponent_model_elo(row), row.get("source"), row.get("time_control"),
            )
        else:
            # Without the Chaos Lens pass the full rule still runs (human-model probabilities from the cache, or
            # computed on a miss), so every game carries the current rule's version, not v1 (ADR 0009).
            await asyncio.to_thread(self._apply_find_rate, game_id)
        # The rule may have changed Brilliant %, so refresh the baseline.
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

    def _classify(self, board: chess.Board, moves: list[chess.Move], user_color: str) -> list[dict]:
        """
        Phase 1. With the chaos pass on, one search per position serves both: classification reads
        the lines the lens pass will need anyway (cached here, so that pass only reads). Without it,
        the classifier's own depth-limited searches.
        """
        if not settings.position_evals_enabled:
            return self.classifier.classify_game(board, moves, user_color)
        with StockfishEngine() as engine:
            # Counting each lookup reports this game's progress to the analysis monitor.
            lines = game_lines(board, moves, monitor.CountingEngine(engine), monitor.CountingStore(SupabaseEvalStore()))
        return self.classifier.classify_game(board, moves, user_color, lines=lines)

    def _first_read(self, user_id: str | None) -> None:
        """Records the owner's first completed game once (plan 3.1: time to first read). Never fails analysis."""
        if not user_id or user_id in self._first_read_done:
            return
        try:
            from app.services.importer import now
            from app.services.settings_store import SettingsStore

            SettingsStore().record_once(user_id, "firstReadAt", now())
            self._first_read_done.add(user_id)  # written now or already set: no need to look again
        except Exception:
            logger.exception("Could not record the first read for %s", user_id)

    def _apply_find_rate(self, game_id: str) -> None:
        """Brilliant find-rate rule (ADR 0004). Never fails the analysis."""
        try:
            BrilliantFindRate().apply(game_id)
        except Exception:
            logger.exception("Brilliant find-rate pass failed for game %s", game_id)

    def _tag_ideas(self, game_id: str) -> None:
        """Intention tagger pass. Never fails the analysis (docs/CHAOS_PLAN.md, rule 1)."""
        try:
            TaggerService().tag_game(game_id)
        except Exception:
            logger.exception("Intention tagging failed for game %s", game_id)

    def _store_chaos_raw_data(
        self,
        game_id: str,
        pgn_text: str,
        board: chess.Board,
        moves: list[chess.Move],
        user_color: str,
        classified: list[dict],
        opponent_rating: int | None = None,
        source: str | None = None,
        time_control: str | None = None,
    ) -> None:
        """
        Chaos Lens raw data: per-ply clocks, cached position evaluations and human
        move probabilities at each ladder Elo.

        Runs after Phase 1 results are saved and never fails the analysis — a problem
        here is logged and the game stays `complete` (docs/CHAOS_PLAN.md, rule 1).
        The outcome is recorded in `games.chaos_data_status` so failed games can be
        found and backfilled instead of silently missing lens data.
        """
        tracker = monitor.current.get()
        if tracker:
            tracker.phase("chaos pass")
        games = get_supabase().table("games")
        try:
            games.update({"clocks_ms": extract_clocks_ms(pgn_text)}).eq("id", game_id).execute()
            with StockfishEngine() as engine:
                stats = evaluate_game_positions(
                    board, moves, user_color, classified, engine, SupabaseEvalStore()
                )
                # Threats for the prophylaxis lens: a short null-move search per position the user faced.
                try:
                    evaluate_game_threats(board, moves, user_color, classified, engine, SupabaseThreatStore())
                except Exception:
                    logger.exception("Threat pass failed for game %s", game_id)
            model = get_human_model_for_game(
                settings.human_model, {"source": source, "time_control": time_control}
            )
            prob_store = SupabaseProbStore()
            elos = elo_ladder(opponent_rating)
            for _ply, position in iter_live_positions(board, moves, user_color, classified):
                for elo in elos:
                    cached_move_probs(position, elo, model, prob_store)
            # Lenses read only what was just stored; no further engine work.
            LensService().score_game(game_id)
            self._apply_find_rate(game_id)
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
            .select("id, pgn, user_color, opponent_rating, source, time_control, chaos_data_status")
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
                game.get("user_color") or "white", moves_res.data, opponent_model_elo(game),
                game.get("source"), game.get("time_control"),
            )
            # Games that stopped after Phase 1 also missed the idea tagger: catch it up too.
            if settings.idea_tagger_enabled:
                await asyncio.to_thread(self._tag_ideas, game["id"])
            done["attempted"] += 1
        if done["attempted"]:
            # The find-rate rule may have changed Brilliant % for these games.
            await self.baseline.recompute_baseline(user_id=settings.local_user_id or None)
        return done

    @staticmethod
    def _record_failure(
        game_id: str, row: dict, exc: BaseException, retryable: bool | None = None
    ) -> dict:
        """Persist the retry budget and a safe diagnosis; return the same fields for the monitor event."""
        attempt = int(row.get("analysis_attempts") or 0) + 1
        retrying = (is_transient(exc) if retryable is None else retryable) and attempt < MAX_ATTEMPTS
        error_type, message = safe_failure(exc)
        failed_at = datetime.now(timezone.utc).isoformat()
        get_supabase().table("games").update({
            "analysis_status": "pending" if retrying else "failed",
            "analysis_attempts": attempt,
            "analysis_error": f"{error_type}: {message}" if message else error_type,
            "analysis_failed_at": failed_at,
        }).eq("id", game_id).execute()
        return {"errorType": error_type, "message": message, "attempt": attempt, "retrying": retrying}

    @staticmethod
    def _release(game_id: str, exc: BaseException) -> dict:
        """Settle an owned processing game even when failure happened outside the main engine pass."""
        try:
            rows = (
                get_supabase().table("games").select("analysis_attempts")
                .eq("id", game_id).eq("analysis_status", "processing").limit(1).execute().data or []
            )
            if rows:
                return AnalysisService._record_failure(game_id, rows[0], exc)
        except Exception:
            logger.exception("Could not release game %s", game_id)
        error_type, message = safe_failure(exc)
        return {"errorType": error_type, "message": message, "attempt": None, "retrying": False}

    @staticmethod
    def requeue_interrupted() -> int:
        """
        On startup: games left 'processing' by a stopped or crashed API go back to 'pending'. Only the process that
        runs analysis calls this, before it starts, so nothing is genuinely in progress yet.
        """
        rows = get_supabase().table("games").update({"analysis_status": "pending"}).eq("analysis_status", "processing").execute().data or []
        if rows:
            logger.info("Requeued %d games interrupted mid-analysis", len(rows))
        return len(rows)

    @staticmethod
    def requeue_orphans(suspects: set[str]) -> set[str]:
        """
        Games marked 'processing' that no analysis in this process is running: a claim whose database answer was
        lost (committed, but the call raised), so no call owns it to hand back. Requeued once seen on two sweeps in
        a row, conditionally, so a game that finished or was released in between is left alone. Returns this
        sweep's suspects for the next one. Only the process that analyses games runs it.
        """
        rows = get_supabase().table("games").select("id").eq("analysis_status", "processing").limit(500).execute().data or []
        orphans = {r["id"] for r in rows} - monitor.busy_games()
        for game_id in orphans & suspects:
            get_supabase().table("games").update({"analysis_status": "pending"}).eq("id", game_id).eq("analysis_status", "processing").execute()
            logger.warning("Requeued game %s: 'processing' with no analysis running", game_id)
        return orphans - suspects

    async def finish_node_games(self) -> int:
        """
        Analyses the games paired nodes have finished searching (ADR 0010): every position is cached, so each takes
        seconds. Run by the main API in a loop when NODE_TOKEN is set, whatever the sync settings.
        """
        from app.services.nodes import NodeService

        ids = await asyncio.to_thread(NodeService().finished_games)
        for game_id in ids:
            try:
                await self.analyze_game(game_id)
            except Exception:
                logger.exception("Finishing node game %s failed", game_id)
        return len(ids)

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
            .order("played_at", desc=True)  # newest first: the game just played comes back first
        )
        if limit is not None:
            query = query.limit(limit)
        if user_id:
            query = query.eq("user_id", user_id)
        if chess_com_username:
            query = query.eq("chess_com_username", chess_com_username)

        # Games a paired node is searching right now are left to it (ADR 0010); they come back cached. Excluded
        # before the limit, so a leased newest game doesn't leave the batch empty.
        try:
            from app.services.nodes import live_leases

            leased = live_leases()
        except Exception:
            leased = set()  # no lease table yet: nothing is leased
        if leased:
            query = query.not_.in_("id", sorted(leased))
        res = query.execute()
        # Several games at once, each with its own single-threaded engine in a worker thread:
        # results stay deterministic (node-limited, fresh hash) and an 8-core PC does ~N× the work.
        gate = asyncio.Semaphore(settings.workers)

        async def one(game_id: str) -> dict | None:
            async with gate:
                return await self.analyze_game(game_id)

        outcomes = await asyncio.gather(*(one(row["id"]) for row in res.data or []), return_exceptions=True)
        results = []
        for row, outcome in zip(res.data or [], outcomes):
            if isinstance(outcome, BaseException):
                # One bad game must not stop the batch. analyze_game already handed the game back if it had
                # claimed it (a failure while storing results would otherwise leave it 'processing' for good).
                logger.error("Analysis failed for game %s: %s", row["id"], outcome)
            elif outcome:
                results.append(outcome)
        return results
