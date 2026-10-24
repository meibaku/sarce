"""
The analysis monitor (dev mode): live machines and engines, throughput history, and the event feed.

`/monitor/stream` pushes the snapshot as server-sent events whenever it changes (checked every couple of seconds),
so the page updates in place without polling; the other routes serve the first paint and the history panels.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.services import monitor

router = APIRouter()
STREAM_S = 2.0


@router.get("/snapshot")
async def snapshot():
    try:
        return await asyncio.to_thread(monitor.snapshot)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/history")
async def history(hours: int = Query(24, ge=1, le=24 * 30), bucket: int = Query(10, ge=1, le=240)):
    return await asyncio.to_thread(monitor.history, hours, bucket)


@router.get("/events")
async def events(limit: int = Query(100, ge=1, le=500), machine: str | None = Query(None, max_length=80)):
    return {"events": await asyncio.to_thread(monitor.events, limit, machine)}


@router.get("/stream")
async def stream(request: Request):
    """Server-sent events: `snapshot` when anything changed, a comment every 15 s to keep the connection open."""

    async def feed():
        last, quiet = None, 0.0
        while not await request.is_disconnected():
            try:
                data = await asyncio.to_thread(monitor.snapshot)
                body = json.dumps({k: v for k, v in data.items() if k != "at"}, default=str, sort_keys=True)
                if body != last:
                    last, quiet = body, 0.0
                    yield f"event: snapshot\ndata: {json.dumps(data, default=str)}\n\n"
                else:
                    quiet += STREAM_S
                    if quiet >= 15:
                        quiet = 0.0
                        yield ": keep-alive\n\n"
            except Exception as exc:  # a database hiccup: say so and keep the stream
                yield f"event: problem\ndata: {json.dumps({'detail': str(exc)[:200]})}\n\n"
            await asyncio.sleep(STREAM_S)

    return StreamingResponse(feed(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
