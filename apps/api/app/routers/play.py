"""Games against Sarce bots only (docs/DESIGN.md, screen 9). Nothing here runs during games elsewhere."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.bots import BOTS, WHY, BotService

router = APIRouter()
bot_service = BotService()


class MoveRequest(BaseModel):
    fen: str
    uci: str | None = None
    bot: str = "defender"
    elo: int = Field(1600, ge=600, le=2600)
    reply: bool = True


@router.get("/bots")
async def list_bots():
    """The Sarce bots and why you might pick each."""
    return {"bots": [{"id": k, "label": v, "why": WHY[k]} for k, v in BOTS.items()]}


@router.post("/start")
async def start_game():
    """A fresh position with its legal moves."""
    return bot_service.start("white")


@router.post("/move")
async def play_move(body: MoveRequest):
    """Applies your move, then the bot's reply (or just the bot's move when `uci` is empty)."""
    try:
        return bot_service.move(body.fen, body.uci, body.bot, body.elo, body.reply)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
