import asyncio
from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import settings
from app.deps import current_user_id, require_game_access, require_pilot_collection_active, resolve_user_id, scoped_user_id
from app.services.importer import FIRST_READ_GAMES, FirstReadImporter
from app.services.analysis import AnalysisService
from app.services.chess_com import ChessComClient, normalize_chess_com_username
from app.services.game_store import GameStore
from app.services.job_queue import JobQueue, queue_analysis
from app.services.lens_service import LensService
from app.services.lichess import LichessClient, normalize_lichess_username, parse_lichess_game
from app.services.pgn_parser import mainline_positions
from app.services.pilot_policy import PilotPolicy
from app.services.review import INTENTS, ReviewService
from app.services.summary import FELT, SummaryService
from app.services.tagger import TaggerService

router = APIRouter()
chess_com = ChessComClient()
lichess = LichessClient()
game_store = GameStore()
importer = FirstReadImporter(chess_com, lichess, game_store)
analysis_service = AnalysisService()
lens_service = LensService()
summary_service = SummaryService()
review_service = ReviewService()
tagger_service = TaggerService()


class ImportRequest(BaseModel):
    """Import recent games from Chess.com public API."""

    username: str = Field(min_length=1, max_length=64)
    user_id: str | None = None
    max_games: int | None = Field(default=None, ge=1, le=1000)
    analyze: bool = Field(default=True, description="Queue Stockfish analysis after import")


class ImportResponse(BaseModel):
    imported: int
    message: str
    username: str


class AnalyzeRequest(BaseModel):
    user_id: str | None = None
    username: str | None = None
    limit: int | None = Field(default=None, ge=1, le=1000)


STYLE_MOMENT_QUALITIES = ("brilliant", "miss", "blunder")


def safe_external_game_url(source: str | None, external_id: str | None) -> str | None:
    """Return only a public game URL on the declared provider, without query data."""
    if not source or not external_id:
        return None
    try:
        parsed = urlsplit(external_id)
    except ValueError:
        return None
    host = (parsed.hostname or "").lower()
    allowed = (
        source == "chess_com" and (host == "chess.com" or host.endswith(".chess.com"))
    ) or (source == "lichess" and (host == "lichess.org" or host.endswith(".lichess.org")))
    if parsed.scheme != "https" or not allowed or parsed.username or parsed.password:
        return None
    return urlunsplit(("https", host, parsed.path, "", ""))


@router.post("/import", response_model=ImportResponse)
async def import_games(body: ImportRequest, background_tasks: BackgroundTasks):
    """
    Fetch Chess.com games by username, store PGNs, optionally analyze.

    The newest FIRST_READ_GAMES are stored and queued before the request answers; older months are fetched and
    queued in the background (plan 3.1, services/importer.py).
    """
    require_pilot_collection_active()
    user_id = resolve_user_id(body.user_id)
    username = normalize_chess_com_username(body.username)
    try:
        archives = await chess_com.fetch_recent_archives(username, limit=None)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Chess.com API error: {exc}") from exc

    if not archives:
        return ImportResponse(
            imported=0,
            message=f"No recent games found for '{username}'",
            username=username,
        )

    try:
        first = await importer.chess_com_first(username, user_id, archives, body.max_games)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Chess.com API error: {exc}") from exc
    stored = first["stored"]

    msg = f"Imported {stored} games for '{username}'."
    if body.analyze and stored > 0:
        queue_analysis(
            background_tasks, analysis_service.analyze_pending,
            user_id=user_id, username=username, limit=stored,
        )
        msg += " Analysis started in background."
    if first["rest"]:
        background_tasks.add_task(
            importer.chess_com_backfill, username, user_id, first["rest"], first["left"],
            analysis_service.analyze_pending if body.analyze else None, first["skip"],
        )
        msg += " Older games are importing in the background."

    return ImportResponse(imported=stored, message=msg, username=username)


@router.post("/import/lichess", response_model=ImportResponse)
async def import_lichess_games(body: ImportRequest, background_tasks: BackgroundTasks):
    """Fetch a user's recent **finished** Lichess games, store them, optionally analyze."""
    require_pilot_collection_active()
    user_id = resolve_user_id(body.user_id)
    username = normalize_lichess_username(body.username)
    wanted = body.max_games or 200
    try:
        stored, first_ids = await importer.lichess_first(username, user_id, wanted)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Lichess API error: {exc}") from exc
    msg = f"Imported {stored} Lichess games for '{username}'."
    if body.analyze and stored > 0:
        queue_analysis(
            background_tasks, analysis_service.analyze_pending,
            user_id=user_id, username=username, limit=stored,
        )
        msg += " Analysis started in background."
    if wanted > FIRST_READ_GAMES:
        # The newest come first (plan 3.1); the rest follow in the background.
        background_tasks.add_task(
            importer.lichess_backfill, username, user_id, wanted, analysis_service.analyze_pending if body.analyze else None, first_ids
        )
    return ImportResponse(imported=stored, message=msg, username=username)


@router.get("")
async def list_games(
    username: str | None = Query(None),
    user_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    chaos: bool = Query(False, description="Only chaos-analysed games, most chaotic first"),
):
    """List imported games with analysis status: newest first, or most chaotic first (`chaos=true`)."""
    from app.db.supabase import get_supabase

    sb = get_supabase()
    query = (
        sb.table("games")
        .select("id, played_at, opponent, opponent_rating, result, time_control, analysis_status, source, external_id, game_analyses(brilliant_pct, total_moves)")
        .order("played_at", desc=True)
        .limit(limit)
    )
    uid = scoped_user_id(user_id, username)
    name = normalize_chess_com_username(username) if username else None
    if uid:
        query = query.eq("user_id", uid)
    if name:
        query = query.eq("chess_com_username", name)

    ranked: dict[str, dict] = {}
    if chaos:
        ranked = {g["gameId"]: g for g in await asyncio.to_thread(lens_service.most_chaotic_games, uid, name, limit)}
        if not ranked:
            return {"games": []}
        query = query.in_("id", list(ranked))

    res = await asyncio.to_thread(query.execute)
    rows = res.data or []
    feedback_by_game: dict[str, str] = {}
    if PilotPolicy.current().enabled and uid and rows:
        feedback_rows = sb.table("pilot_read_feedback").select("game_id, resonance").eq(
            "user_id", uid
        ).in_("game_id", [row["id"] for row in rows]).execute().data or []
        feedback_by_game = {row["game_id"]: row["resonance"] for row in feedback_rows}
    games = []
    for row in rows:
        analysis = row.pop("game_analyses", None)
        summary = analysis[0] if isinstance(analysis, list) and analysis else analysis
        games.append(
            {
                "id": row["id"],
                "playedAt": row.get("played_at"),
                "opponent": row.get("opponent"),
                "opponentRating": row.get("opponent_rating"),
                "result": row.get("result"),
                "timeControl": row.get("time_control"),
                "analysisStatus": row.get("analysis_status"),
                "brilliantPct": summary.get("brilliant_pct") if summary else None,
                "totalMoves": summary.get("total_moves") if summary else None,
                "pilotResonance": feedback_by_game.get(row["id"]),
                "externalUrl": safe_external_game_url(row.get("source"), row.get("external_id")),
                **({k: v for k, v in ranked[row["id"]].items() if k != "gameId"} if row["id"] in ranked else {}),
            }
        )
    if chaos:
        games.sort(key=lambda g: (-g["chaosPeak"], -g["realChaos"], g["id"]))
    return {"games": games}


@router.get("/jobs")
async def list_analysis_jobs(user_id: str | None = Query(None)):
    """The caller's recent analysis jobs (empty unless the job queue is enabled)."""
    if not settings.job_queue_enabled:
        return {"jobs": []}
    try:
        return {"jobs": JobQueue().recent(resolve_user_id(user_id))}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/moments")
async def list_style_moments(
    username: str | None = Query(None),
    user_id: str | None = Query(None),
    limit: int = Query(8, ge=1, le=50),
):
    """Recent notable moves for the dashboard companion view."""
    from app.db.supabase import get_supabase

    sb = get_supabase()
    games_query = (
        sb.table("games")
        .select("id, played_at, opponent, result")
        .eq("analysis_status", "complete")
        .order("played_at", desc=True)
        .limit(50)
    )
    uid = scoped_user_id(user_id, username)
    if uid:
        games_query = games_query.eq("user_id", uid)
    if username:
        games_query = games_query.eq("chess_com_username", normalize_chess_com_username(username))

    games_res = games_query.execute()
    games = games_res.data or []
    game_ids = [g["id"] for g in games]
    if not game_ids:
        return {"moments": []}

    moves_res = (
        sb.table("game_moves")
        .select("game_id, ply, uci, san, quality, cp_loss, eval_before, eval_after, is_brilliant, phase, signals, highlight, best_uci, best_san, pv")
        .in_("game_id", game_ids)
        .in_("quality", list(STYLE_MOMENT_QUALITIES))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    games_by_id = {g["id"]: g for g in games}
    moments = []
    for move in moves_res.data or []:
        game = games_by_id.get(move["game_id"], {})
        moments.append(
            {
                "gameId": move["game_id"],
                "playedAt": game.get("played_at"),
                "opponent": game.get("opponent"),
                "result": game.get("result"),
                "ply": move.get("ply"),
                "uci": move.get("uci"),
                "san": move.get("san"),
                "quality": move.get("quality"),
                "cpLoss": float(move["cp_loss"]) if move.get("cp_loss") is not None else None,
                "evalBefore": float(move["eval_before"]) if move.get("eval_before") is not None else None,
                "evalAfter": float(move["eval_after"]) if move.get("eval_after") is not None else None,
                "isBrilliant": move.get("is_brilliant"),
                "phase": move.get("phase"),
                "signals": move.get("signals") or [],
                "highlight": move.get("highlight"),
                "bestUci": move.get("best_uci"),
                "bestSan": move.get("best_san"),
                "pv": move.get("pv") or [],
            }
        )

    return {"moments": moments}


@router.get("/{game_id}")
async def get_game_detail(
    game_id: str,
    username: str | None = Query(None),
    user_id: str | None = Query(None),
):
    """Game metadata plus classified user moves."""
    from app.db.supabase import get_supabase

    sb = get_supabase()
    game_res = (
        sb.table("games")
        .select("id, pgn, played_at, opponent, opponent_rating, result, user_color, time_control, analysis_status, game_analyses(brilliant_pct, distribution, total_moves)")
        .eq("id", game_id)
    )
    uid = scoped_user_id(user_id, username)
    if uid:
        game_res = game_res.eq("user_id", uid)
    if username:
        username = normalize_chess_com_username(username)
        game_res = game_res.eq("chess_com_username", username)

    game_res = game_res.maybe_single().execute()
    if not game_res or not game_res.data:
        raise HTTPException(status_code=404, detail="Game not found")

    game = game_res.data
    moves_res = (
        sb.table("game_moves")
        .select("ply, uci, san, quality, cp_loss, eval_before, eval_after, is_brilliant, phase, signals, highlight, best_uci, best_san, pv, games!inner(user_id, chess_com_username)")
        .eq("game_id", game["id"])
    )
    if uid:
        moves_res = moves_res.eq("games.user_id", uid)
    if username:
        moves_res = moves_res.eq("games.chess_com_username", username)

    moves_res = moves_res.order("ply").execute()

    analyses = game.pop("game_analyses", None)
    analysis = analyses[0] if isinstance(analyses, list) and analyses else analyses
    pgn_text = game.pop("pgn", "") or ""
    initial_fen, mainline = mainline_positions(pgn_text)
    return {
        "id": game["id"],
        "playedAt": game.get("played_at"),
        "opponent": game.get("opponent"),
        "opponentRating": game.get("opponent_rating"),
        "result": game.get("result"),
        "userColor": game.get("user_color"),
        "timeControl": game.get("time_control"),
        "analysisStatus": game.get("analysis_status"),
        "brilliantPct": float(analysis.get("brilliant_pct", 0)) if analysis else None,
        "distribution": analysis.get("distribution") if analysis else None,
        "totalMoves": analysis.get("total_moves") if analysis else None,
        "initialFen": initial_fen,
        "mainline": mainline,
        "moves": [
            {
                "ply": move.get("ply"),
                "uci": move.get("uci"),
                "san": move.get("san"),
                "quality": move.get("quality"),
                "cpLoss": float(move["cp_loss"]) if move.get("cp_loss") is not None else None,
                "evalBefore": float(move["eval_before"]) if move.get("eval_before") is not None else None,
                "evalAfter": float(move["eval_after"]) if move.get("eval_after") is not None else None,
                "isBrilliant": move.get("is_brilliant"),
                "phase": move.get("phase"),
                "signals": move.get("signals") or [],
                "highlight": move.get("highlight"),
                "bestUci": move.get("best_uci"),
                "bestSan": move.get("best_san"),
                "pv": move.get("pv") or [],
            }
            for move in moves_res.data or []
        ],
    }


@router.get("/{game_id}/lenses")
async def get_game_lenses(
    game_id: str,
    refresh: bool = Query(False, description="Re-score from stored raw data (no engine run)"),
):
    """Per-move lens results (soundness, chaos, survival) for a game."""
    PilotPolicy.current().require("chaos")
    require_game_access(game_id)
    try:
        if refresh and lens_service.score_game(game_id) is None:
            raise HTTPException(status_code=404, detail="Game not found")
        return {
            "gameId": game_id,
            "moves": lens_service.get_game_lenses(game_id),
            "clocksMs": lens_service.get_game_clocks(game_id),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{game_id}/ideas")
async def get_game_ideas(
    game_id: str,
    refresh: bool = Query(False, description="Re-tag from the PGN and stored evals (no engine run)"),
):
    """Motif tags per ply and the user's idea windows for a game."""
    PilotPolicy.current().require("chaos")
    require_game_access(game_id)
    try:
        if refresh and tagger_service.tag_game(game_id) is None:
            raise HTTPException(status_code=404, detail="Game not found")
        return tagger_service.get_game_ideas(game_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/analyze")
async def analyze_pending(body: AnalyzeRequest, background_tasks: BackgroundTasks):
    """Trigger analysis for pending games (manual or after import)."""
    require_pilot_collection_active()
    user_id = current_user_id() or (resolve_user_id(body.user_id) if body.user_id else None)
    username = normalize_chess_com_username(body.username) if body.username else None

    queue_analysis(
        background_tasks, analysis_service.analyze_pending,
        user_id=user_id, username=username, limit=body.limit,
    )
    return {
        "message": "Analysis queued for all pending games"
        if body.limit is None
        else f"Analysis queued (limit {body.limit})",
        "username": username,
        "userId": user_id or settings.local_user_id,
    }


class FeltRequest(BaseModel):
    answer: str = Field(description="yes | partly | no")


@router.get("/{game_id}/summary")
async def get_game_summary(game_id: str):
    """After-game Summary: headline, outcome, this game's Brilliant %, moments and the one question."""
    require_game_access(game_id)
    data = summary_service.summary(game_id, current_user_id(), resolve_user_id(None))
    if data is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return data


@router.post("/{game_id}/felt")
async def set_game_felt(game_id: str, body: FeltRequest):
    """Records the answer to "Did this game feel like you?"."""
    require_game_access(game_id)
    if body.answer not in FELT:
        raise HTTPException(status_code=422, detail=f"answer must be one of {list(FELT)}")
    summary_service.set_felt(game_id, body.answer)
    return {"gameId": game_id, "felt": body.answer}


class IntentRequest(BaseModel):
    type: str | None = Field(None, description="calculated | intuitive | bluff")
    note: str = Field("", max_length=2000)


@router.get("/{game_id}/review")
async def get_game_review(game_id: str):
    """Review: every moment with its board, squares that mattered, P_fail ladder, mirror line and note."""
    require_game_access(game_id)
    data = review_service.review(game_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return PilotPolicy.current().filter_review(data)


@router.get("/{game_id}/moves/{ply}/why")
async def why_this_move(game_id: str, ply: int):
    """
    "Why this move?": the badge's reason, each Brilliant rule as a check with its numbers, the chaos
    numbers, and playable lines (your move and the reply, the engine's top lines, a sacrifice that would count).
    """
    from app.routers.play import bot_service
    from app.services.explain import ExplainService

    require_game_access(game_id)
    data = await asyncio.to_thread(ExplainService(bot_service).why, game_id, ply)  # live lines use the engine
    if data is None:
        raise HTTPException(status_code=404, detail="Not one of your analysed moves.")
    return PilotPolicy.current().filter_explanation(data)


@router.put("/{game_id}/moves/{ply}/intent")
async def save_move_intent(game_id: str, ply: int, body: IntentRequest):
    """Saves the player's intent note for a moment (one per move; editing replaces it)."""
    require_pilot_collection_active()
    require_game_access(game_id)
    if body.type is not None and body.type not in INTENTS:
        raise HTTPException(status_code=422, detail=f"type must be one of {list(INTENTS)}")
    return review_service.save_intent(game_id, ply, body.type, body.note, current_user_id())


class BrilliantReportRequest(BaseModel):
    source: str = Field(default="chess_com", pattern="^(chess_com|lichess)$")


@router.post("/{game_id}/moves/{ply}/brilliant-report")
async def report_brilliant(game_id: str, ply: int, body: BrilliantReportRequest):
    """"Chess.com called this Brilliant": stores the report and says which clause Sarce's rule stopped at (plan 3.3)."""
    from app.services.brilliant_reports import BrilliantReportService

    require_game_access(game_id)
    result = await asyncio.to_thread(BrilliantReportService().report, game_id, ply, body.source, current_user_id())
    if result is None:
        raise HTTPException(status_code=404, detail="Not one of your analysed moves.")
    return result


class CheckinRequest(BaseModel):
    ply: int
    answer: str
    flagged: bool = False


@router.post("/{game_id}/checkin")
async def answer_checkin(game_id: str, body: CheckinRequest):
    """Records the answer to "Was something going on here?" (and whether the move had been flagged)."""
    require_game_access(game_id)
    try:
        summary_service.set_checkin(game_id, body.ply, body.answer, body.flagged)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"gameId": game_id, "ply": body.ply, "answer": body.answer}
