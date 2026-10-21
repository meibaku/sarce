"""Games against Sarce bots only (docs/DESIGN.md, screen 9). Nothing here runs during games elsewhere."""

from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.deps import resolve_user_id
from app.services.bots import BOTS, WHY, BotService
from app.services.job_queue import queue_analysis

router = APIRouter()
bot_service = BotService()


class MoveRequest(BaseModel):
    fen: str
    uci: str | None = None
    bot: str = "defender"
    elo: int = Field(1600, ge=600, le=2600)
    reply: bool = True


class SaveRequest(BaseModel):
    bot: str = "defender"
    moves: list[str] = Field(..., min_length=1, max_length=600)
    result: Literal["win", "loss", "draw"]
    clocks_ms: list[int | None] | None = Field(None, max_length=600)
    elo: int = Field(1600, ge=600, le=2600)


@router.get("/bots")
async def list_bots():
    """The Sarce bots and why you might pick each."""
    return {"bots": [{"id": k, "label": v, "why": WHY[k]} for k, v in BOTS.items()]}


@router.post("/start")
async def start_game():
    """A fresh position with its legal moves."""
    return bot_service.start("white")


@router.post("/save")
async def save_game(body: SaveRequest, background_tasks: BackgroundTasks):
    """Saves a finished bot game and queues its analysis, so it opens in Summary and Review."""
    from app.routers.games import analysis_service

    owner = resolve_user_id(None)
    try:
        game_id = bot_service.save(owner, body.bot, body.moves, body.result, body.clocks_ms, body.elo)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    queue_analysis(background_tasks, analysis_service.analyze_pending, user_id=owner, username=None, limit=1)
    return {"gameId": game_id}


@router.post("/move")
async def play_move(body: MoveRequest):
    """Applies your move, then the bot's reply (or just the bot's move when `uci` is empty)."""
    try:
        return bot_service.move(body.fen, body.uci, body.bot, body.elo, body.reply)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
