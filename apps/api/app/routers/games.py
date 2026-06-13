from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import settings
from app.deps import resolve_user_id
from app.services.analysis import AnalysisService
from app.services.chess_com import ChessComClient
from app.services.game_store import GameStore

router = APIRouter()
chess_com = ChessComClient()
game_store = GameStore()
analysis_service = AnalysisService()


class ImportRequest(BaseModel):
    """Import recent games from Chess.com public API."""

    username: str = Field(min_length=1, max_length=64)
    user_id: str | None = None
    max_games: int = Field(default=5, ge=1, le=20)
    analyze: bool = Field(default=True, description="Queue Stockfish analysis after import")


class ImportResponse(BaseModel):
    imported: int
    message: str
    username: str


class AnalyzeRequest(BaseModel):
    user_id: str | None = None
    username: str | None = None
    limit: int = Field(default=5, ge=1, le=10)


@router.post("/import", response_model=ImportResponse)
async def import_games(body: ImportRequest, background_tasks: BackgroundTasks):
    """
    Fetch Chess.com games by username, store PGNs, optionally analyze.

    Phase 1: imports last archives, parses PGN via python-chess, stores metadata.
    """
    user_id = resolve_user_id(body.user_id)
    try:
        archives = await chess_com.fetch_recent_archives(body.username, limit=2)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Chess.com API error: {exc}") from exc

    if not archives:
        return ImportResponse(
            imported=0,
            message=f"No recent games found for '{body.username}'",
            username=body.username,
        )

    games = []
    for archive_url in archives:
        batch = await chess_com.fetch_games_from_archive(archive_url)
        games.extend(batch)
        if len(games) >= body.max_games:
            break

    games = games[: body.max_games]
    stored = await game_store.store_imported_games(
        username=body.username,
        user_id=user_id,
        games=games,
    )

    msg = f"Imported {stored} games for '{body.username}'."
    if body.analyze and stored > 0:
        background_tasks.add_task(
            analysis_service.analyze_pending,
            user_id=user_id,
            chess_com_username=body.username,
            limit=stored,
        )
        msg += " Analysis started in background."

    return ImportResponse(imported=stored, message=msg, username=body.username)


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
        .select("id, played_at, opponent, opponent_rating, result, analysis_status, game_analyses(brilliant_pct, total_moves)")
        .order("played_at", desc=True)
        .limit(limit)
    )
    uid = resolve_user_id(user_id) if user_id or not username else None
    if uid:
        query = query.eq("user_id", uid)
    if username:
        query = query.eq("chess_com_username", username)

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
                "analysisStatus": row.get("analysis_status"),
                "brilliantPct": summary.get("brilliant_pct") if summary else None,
                "totalMoves": summary.get("total_moves") if summary else None,
            }
        )
    return {"games": games}


@router.post("/analyze")
async def analyze_pending(body: AnalyzeRequest, background_tasks: BackgroundTasks):
    """Trigger analysis for pending games (manual or after import)."""
    user_id = resolve_user_id(body.user_id) if body.user_id else None

    async def run():
        await analysis_service.analyze_pending(
            user_id=user_id,
            chess_com_username=body.username,
            limit=body.limit,
        )

    background_tasks.add_task(run)
    return {
        "message": f"Analysis queued (limit {body.limit})",
        "username": body.username,
        "userId": user_id or settings.local_user_id,
    }
