from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import settings
from app.deps import current_user_id, require_game_access, resolve_user_id, scoped_user_id
from app.services.analysis import AnalysisService
from app.services.chess_com import ChessComClient, normalize_chess_com_username
from app.services.game_store import GameStore
from app.services.job_queue import JobQueue, queue_analysis
from app.services.lens_service import LensService
from app.services.lichess import LichessClient, normalize_lichess_username, parse_lichess_game
from app.services.pgn_parser import mainline_positions
from app.services.review import INTENTS, ReviewService
from app.services.summary import FELT, SummaryService
from app.services.tagger import TaggerService

router = APIRouter()
chess_com = ChessComClient()
lichess = LichessClient()
game_store = GameStore()
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


@router.post("/import", response_model=ImportResponse)
async def import_games(body: ImportRequest, background_tasks: BackgroundTasks):
    """
    Fetch Chess.com games by username, store PGNs, optionally analyze.

    Phase 1: imports last archives, parses PGN via python-chess, stores metadata.
    """
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

    games = []
    try:
        for archive_url in archives:
            batch = await chess_com.fetch_games_from_archive(archive_url)
            games.extend(batch)
            if body.max_games is not None and len(games) >= body.max_games:
                break
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Chess.com API error: {exc}") from exc

    if body.max_games is not None:
        games = games[: body.max_games]
    stored = await game_store.store_imported_games(
        username=username,
        user_id=user_id,
        games=games,
    )

    msg = f"Imported {stored} games for '{username}'."
    if body.analyze and stored > 0:
        queue_analysis(
            background_tasks, analysis_service.analyze_pending,
            user_id=user_id, username=username, limit=stored,
        )
        msg += " Analysis started in background."

    return ImportResponse(imported=stored, message=msg, username=username)


@router.post("/import/lichess", response_model=ImportResponse)
async def import_lichess_games(body: ImportRequest, background_tasks: BackgroundTasks):
    """Fetch a user's recent **finished** Lichess games, store them, optionally analyze."""
    user_id = resolve_user_id(body.user_id)
    username = normalize_lichess_username(body.username)
    try:
        raw_games = await lichess.fetch_games(username, max_games=body.max_games or 200)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Lichess API error: {exc}") from exc

    parsed = [game for raw in raw_games if (game := parse_lichess_game(raw, username))]
    stored = await game_store.store_parsed_games(
        username=username, parsed_games=parsed, source="lichess", user_id=user_id
    )
    msg = f"Imported {stored} Lichess games for '{username}'."
    if body.analyze and stored > 0:
        queue_analysis(
            background_tasks, analysis_service.analyze_pending,
            user_id=user_id, username=username, limit=stored,
        )
        msg += " Analysis started in background."
    return ImportResponse(imported=stored, message=msg, username=username)


@router.get("")
async def list_games(
    username: str | None = Query(None),
    user_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    """List imported games with analysis status."""
    from app.db.supabase import get_supabase

    sb = get_supabase()
    query = (
        sb.table("games")
        .select("id, played_at, opponent, opponent_rating, result, time_control, analysis_status, game_analyses(brilliant_pct, total_moves)")
        .order("played_at", desc=True)
        .limit(limit)
    )
    uid = scoped_user_id(user_id, username)
    if uid:
        query = query.eq("user_id", uid)
    if username:
        query = query.eq("chess_com_username", normalize_chess_com_username(username))

    res = query.execute()
    games = []
    for row in res.data or []:
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
            }
        )
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
    if not game_res.data:
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
    return data


@router.put("/{game_id}/moves/{ply}/intent")
async def save_move_intent(game_id: str, ply: int, body: IntentRequest):
    """Saves the player's intent note for a moment (one per move; editing replaces it)."""
    require_game_access(game_id)
    if body.type is not None and body.type not in INTENTS:
        raise HTTPException(status_code=422, detail=f"type must be one of {list(INTENTS)}")
    return review_service.save_intent(game_id, ply, body.type, body.note, current_user_id())


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
