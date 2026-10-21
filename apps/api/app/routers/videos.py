"""
Positions from videos (PHASES 2.2-2.4): the transcript around a moment, and opt-in AI help to read a
board from a screenshot or summarise what was said. AI calls need server credentials **and** the
player's Settings opt-in (`aiHelp`); otherwise they answer 403 and the UI offers the manual way.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.deps import resolve_user_id
from app.services import ai
from app.services.settings_store import SettingsStore
from app.services.video import CaptionsBlocked, excerpt, fetch_snippets, parse_pasted, start_seconds, youtube_id

router = APIRouter()


class ExcerptRequest(BaseModel):
    url: str = Field(..., max_length=500)
    at: int | None = Field(None, ge=0, le=86_400, description="Seconds into the video; defaults to the URL's t=")
    transcript: str | None = Field(None, max_length=400_000, description="Pasted from YouTube's Show transcript, when captions can't be fetched")


class ImageRequest(BaseModel):
    data: str = Field(..., max_length=8_000_000, description="Base64 image")
    mediaType: str = Field(..., max_length=40)


class SummaryRequest(BaseModel):
    excerpt: str = Field(..., max_length=12_000)
    fen: str | None = Field(None, max_length=120)


def require_ai(user_id: str | None) -> None:
    if not ai.credentials_present():
        raise HTTPException(status_code=403, detail="AI help isn't set up on this server (no Claude credentials).")
    if not SettingsStore().get(resolve_user_id(user_id)).get("aiHelp"):
        raise HTTPException(status_code=403, detail="Turn on Settings → Video help (sent to AI) first.")


@router.post("/excerpt")
async def video_excerpt(body: ExcerptRequest):
    """
    The captions around a moment (no AI): {videoId, at, text, start, end}. With `transcript` (pasted from
    YouTube's "Show transcript"), that text is used instead of fetching, e.g. when YouTube blocks the request.
    """
    video = youtube_id(body.url)
    if not video:
        raise HTTPException(status_code=422, detail="That isn't a YouTube link.")
    at = body.at if body.at is not None else (start_seconds(body.url) or 0)
    if body.transcript and body.transcript.strip():
        pasted = parse_pasted(body.transcript)
        if len(pasted) == 1 and pasted[0]["start"] == 0.0:  # no timestamps: the player pasted just the part they want
            return {"videoId": video, "at": at, "text": pasted[0]["text"][:6000], "start": at, "end": at, "pasted": True}
        return {"videoId": video, "at": at, **excerpt(pasted, at), "pasted": True}
    try:
        snippets = fetch_snippets(video)
    except CaptionsBlocked as exc:
        raise HTTPException(
            status_code=503,
            detail="YouTube is blocking caption requests from this network. Paste the transcript instead (… → Show transcript on YouTube).",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=404, detail="This video has no captions Sarce can read.") from exc
    return {"videoId": video, "at": at, **excerpt(snippets, at)}


@router.post("/fen-from-image")
async def fen_from_image(body: ImageRequest, user_id: str | None = Query(None)):
    """Opt-in: read a board from a screenshot with Claude; the FEN is checked by python-chess."""
    require_ai(user_id)
    try:
        return ai.fen_from_image(body.data, body.mediaType)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/summary")
async def summarize(body: SummaryRequest, user_id: str | None = Query(None)):
    """Opt-in: a short title, summary and ideas from a transcript excerpt."""
    require_ai(user_id)
    try:
        return ai.summarize_excerpt(body.excerpt, body.fen)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
