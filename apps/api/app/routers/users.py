import asyncio

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.deps import current_user_id, resolve_user_id, scoped_user_id

from app.services.chaos_map import CHAOS_DRILL, ChaosMapService
from app.services.chess_com import normalize_chess_com_username
from app.services.home import HomeService
from app.services.lens_service import LensService
from app.services.library import LibraryService
from app.services.recap import INTENTS, FOCUSES, RecapService
from app.services.settings_store import SettingsStore
from app.services.sync import SyncService
from app.services.train import TrainService
from app.services.you import YouService

router = APIRouter()
lens_service = LensService()
home_service = HomeService()
you_service = YouService()
library_service = LibraryService()
recap_service = RecapService()
train_service = TrainService()
settings_store = SettingsStore()
sync_service = SyncService()
chaos_map_service = ChaosMapService()
_chaos_map_building: set[str] = set()  # owners whose map is being rebuilt right now


@router.get("/home")
async def get_home(username: str | None = Query(None), user_id: str | None = Query(None)):
    """Home screen: the latest game's style read and moments, and the Brilliant card."""
    name = normalize_chess_com_username(username) if username else None
    try:
        # Heavy, synchronous database work: run it off the event loop so other requests keep flowing.
        return await asyncio.to_thread(home_service.home, scoped_user_id(user_id, username), name)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/you")
async def get_you(username: str | None = Query(None), user_id: str | None = Query(None)):
    """You: Brilliant trend and formula, style fingerprint, reference axes, time controls, survival."""
    name = normalize_chess_com_username(username) if username else None
    try:
        return await asyncio.to_thread(you_service.you, scoped_user_id(user_id, username), name)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/sacrifices")
async def get_sacrifices(username: str | None = Query(None), user_id: str | None = Query(None)):
    """Sacrifice library: every sacrifice played, newest first, with what was offered and the note."""
    name = normalize_chess_com_username(username) if username else None
    try:
        return {"sacrifices": await asyncio.to_thread(library_service.sacrifices, scoped_user_id(user_id, username), name)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class FocusRequest(BaseModel):
    kind: str
    value: str


@router.get("/recap")
async def get_recap(user_id: str | None = Query(None)):
    """Weekly recap: the week's games, Brilliant, best moment, last focus and next week's options."""
    data = await asyncio.to_thread(recap_service.recap, scoped_user_id(user_id, None), resolve_user_id(user_id))
    if data is None:
        raise HTTPException(status_code=404, detail="No analysed games yet")
    return data


@router.get("/focus")
async def get_focus(user_id: str | None = Query(None)):
    """The current weekly focus and today's intention, with the choices for each."""
    owner = resolve_user_id(user_id)
    return {
        "weekly": recap_service.current_focus(owner, "weekly"),
        "today": recap_service.current_focus(owner, "today"),
        "focuses": FOCUSES,
        "intents": INTENTS,
    }


@router.put("/focus")
async def set_focus(body: FocusRequest, user_id: str | None = Query(None)):
    """Sets next week's focus (kind=weekly) or today's intention (kind=today)."""
    if body.kind not in ("weekly", "today"):
        raise HTTPException(status_code=422, detail="kind must be weekly or today")
    try:
        return recap_service.set_focus(resolve_user_id(user_id), body.kind, body.value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class DrillAnswer(BaseModel):
    drillKey: str
    confidence: str


class DrillMove(BaseModel):
    fen: str
    uci: str = Field(..., min_length=4, max_length=5)
    answer: str | None = None
    source: str | None = None


@router.post("/train/check")
async def check_drill_move(body: DrillMove):
    """Checks your move in a drill on the server (legality, the answer, and whether it still holds)."""
    from app.routers.play import bot_service
    from app.services.train import check_move

    try:
        return check_move(
            body.fen, body.uci, body.answer, body.source == "find the sacrifice", bot_service.move_loss,
            # "<Master> in your openings" drills: the answer is that player's move, so feedback names them.
            reference_player=body.source.removesuffix(" in your openings") if (body.source or "").endswith(" in your openings") else None,
            chaos_drill=body.source == CHAOS_DRILL,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class SavePosition(BaseModel):
    fen: str = Field(..., max_length=120)
    title: str | None = Field(None, max_length=200)
    note: str | None = Field(None, max_length=4000)
    gameId: str | None = None
    ply: int | None = Field(None, ge=0, le=1200)
    sourceUrl: str | None = Field(None, max_length=500)
    sourceTimeS: int | None = Field(None, ge=0, le=86_400)
    excerpt: str | None = Field(None, max_length=12_000)
    aiSummary: str | None = Field(None, max_length=4000)


@router.get("/positions")
async def list_positions(user_id: str | None = Query(None), q: str | None = Query(None, max_length=200)):
    """Positions you saved to drill (Review → Add to Train, videos); `q` searches titles, notes and transcripts."""
    from app.services.positions import PositionStore

    return {"positions": PositionStore().list(resolve_user_id(user_id), q=q)}


@router.post("/positions")
async def save_position(body: SavePosition, user_id: str | None = Query(None)):
    """Saves a position for Train; the engine's move from the game's analysis becomes the answer."""
    from app.services.positions import PositionStore

    try:
        source = (
            {"url": body.sourceUrl, "time_s": body.sourceTimeS, "excerpt": body.excerpt, "ai_summary": body.aiSummary}
            if body.sourceUrl or body.excerpt or body.aiSummary
            else None
        )
        return PositionStore().save(resolve_user_id(user_id), body.fen, body.title, body.note, body.gameId, body.ply, source)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/positions/{position_id}")
async def delete_position(position_id: str, user_id: str | None = Query(None)):
    from app.services.positions import PositionStore

    PositionStore().delete(resolve_user_id(user_id), position_id)
    return {"deleted": position_id}


@router.get("/train")
async def get_train(user_id: str | None = Query(None), drill: str | None = Query(None, max_length=200)):
    """Train queue: drills from your games, the trap atlas and saved positions, aimed at this week's focus."""
    owner = resolve_user_id(user_id)
    focus = recap_service.current_focus(owner, "weekly")
    data = await asyncio.to_thread(train_service.queue, scoped_user_id(user_id, None), owner, focus, first=drill)
    return {**data, "focus": FOCUSES.get(focus or "")}


@router.post("/train/answer")
async def answer_drill(body: DrillAnswer, user_id: str | None = Query(None)):
    """Records "How sure were you?" and schedules the drill (tomorrow / 3 days / 9 days)."""
    try:
        return train_service.answer(resolve_user_id(user_id), body.drillKey, body.confidence)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/settings")
async def get_settings(user_id: str | None = Query(None)):
    """Style goal and preferences, plus what Sarce keeps."""
    from app.services.ai import credentials_present

    owner = resolve_user_id(user_id)
    return {
        **settings_store.get(owner),
        "kept": settings_store.kept(owner, scoped_user_id(user_id, None)),
        # Whether this server can use AI help at all; the player still has to opt in (aiHelp).
        "aiAvailable": credentials_present(),
    }


@router.put("/settings")
async def update_settings(changes: dict = Body(...), user_id: str | None = Query(None)):
    """Updates any of: goalLo, goalHi, questionBudget, quietUntil, sources, theme, playfulMascot, motion."""
    try:
        return settings_store.update(resolve_user_id(user_id), changes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/journal", response_class=PlainTextResponse)
async def export_journal(user_id: str | None = Query(None)):
    """The journal as Markdown (sacrifices and notes), for download or printing to PDF."""
    owner = resolve_user_id(user_id)
    return PlainTextResponse(
        settings_store.journal(owner, scoped_user_id(user_id, None)),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="sarce-journal.md"'},
    )


@router.get("/sync")
async def sync_status(user_id: str | None = Query(None)):
    """Saved usernames, when the last sync ran, and how many games wait for analysis."""
    return sync_service.status(resolve_user_id(user_id), scoped_user_id(user_id, None))


@router.post("/sync")
async def sync_now(background_tasks: BackgroundTasks, user_id: str | None = Query(None)):
    """Fetches new finished games now; analysis of them continues in the background."""
    from app.routers.games import analysis_service

    owner = resolve_user_id(user_id)
    background_tasks.add_task(sync_service.sync, owner, analysis_service.analyze_pending)
    return {"started": True}


@router.get("/chaos-map")
async def get_chaos_map(user_id: str | None = Query(None)):
    """Your chaos map: frequent opening positions and the sound move that asks the most of your opponents."""
    owner = resolve_user_id(user_id)
    return {"positions": chaos_map_service.get(owner), "building": owner in _chaos_map_building}


def _build_chaos_map(owner: str) -> None:
    try:
        chaos_map_service.build(owner)
    finally:
        _chaos_map_building.discard(owner)


@router.post("/chaos-map")
async def rebuild_chaos_map(background_tasks: BackgroundTasks, user_id: str | None = Query(None)):
    """Rebuilds the map in the background (a minute or two of engine work); GET shows it when done."""
    owner = resolve_user_id(user_id)
    if owner not in _chaos_map_building:
        _chaos_map_building.add(owner)
        background_tasks.add_task(_build_chaos_map, owner)
    return {"building": True}


@router.get("/{username}/chaos-summary")
async def get_chaos_summary(username: str):
    """Counts of real / cheap / calculated chaos and the survival rate for a player."""
    try:
        return lens_service.chaos_summary(
            normalize_chess_com_username(username), user_id=current_user_id()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
