from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import settings
from app.deps import resolve_user_id
from app.services.analysis import AnalysisService
from app.services.chess_com import ChessComClient, normalize_chess_com_username
from app.services.game_store import GameStore
from app.services.pgn_parser import mainline_positions

router = APIRouter()
chess_com = ChessComClient()
game_store = GameStore()
analysis_service = AnalysisService()


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
        background_tasks.add_task(
            analysis_service.analyze_pending,
            user_id=user_id,
            chess_com_username=username,
            limit=stored,
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
    uid = resolve_user_id(user_id) if user_id or not username else None
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
    uid = resolve_user_id(user_id) if user_id or not username else None
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
    uid = resolve_user_id(user_id) if user_id or not username else None
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


@router.post("/analyze")
async def analyze_pending(body: AnalyzeRequest, background_tasks: BackgroundTasks):
    """Trigger analysis for pending games (manual or after import)."""
    user_id = resolve_user_id(body.user_id) if body.user_id else None
    username = normalize_chess_com_username(body.username) if body.username else None

    async def run():
        await analysis_service.analyze_pending(
            user_id=user_id,
            chess_com_username=username,
            limit=body.limit,
        )

    background_tasks.add_task(run)
    return {
        "message": "Analysis queued for all pending games"
        if body.limit is None
        else f"Analysis queued (limit {body.limit})",
        "username": username,
        "userId": user_id or settings.local_user_id,
    }
