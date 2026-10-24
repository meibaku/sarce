"""
The node gateway (ADR 0010): the only door a paired Sarce Node uses, as its own small server.

Run it next to the API, bound to the private link the nodes share (here the Ethernet cable):
    uvicorn app.node_gateway:app --host 10.77.0.1 --port 8002

Every route needs the pairing token in `X-Sarce-Node` (NODE_TOKEN in the server's .env); without one configured,
nothing is accepted. The main API keeps listening on localhost only.
"""

from __future__ import annotations

import asyncio

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from pydantic import BaseModel, Field

from app.services.nodes import NodeService, bundle, signature, token_ok

service = NodeService()


def paired(x_sarce_node: str | None = Header(default=None)) -> None:
    if not token_ok(x_sarce_node):
        raise HTTPException(status_code=401, detail="Not a paired node")


app = FastAPI(title="Sarce node gateway", dependencies=[Depends(paired)], docs_url=None, redoc_url=None, openapi_url=None)


class NodeRequest(BaseModel):
    node: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")


class RowsRequest(NodeRequest):
    gameId: str
    evals: list[dict] = Field(default_factory=list, max_length=200)
    threats: list[dict] = Field(default_factory=list, max_length=200)


class DoneRequest(NodeRequest):
    gameId: str


@app.get("/nodes/config")
async def config():
    return service.config()


@app.get("/nodes/bundle.zip")
async def get_bundle():
    data, version = bundle()
    # Signed with the pairing token: a node refuses a bundle someone on the network swapped in.
    return Response(content=data, media_type="application/zip", headers={"X-Sarce-Version": version, "X-Sarce-Signature": signature(data)})


@app.post("/nodes/claim")
async def claim(body: NodeRequest):
    job = await asyncio.to_thread(service.claim, body.node)
    return {"job": job}


@app.post("/nodes/rows")
async def rows(body: RowsRequest):
    return {"stored": await asyncio.to_thread(service.put_rows, body.gameId, body.node, body.evals, body.threats)}


@app.post("/nodes/heartbeat")
async def heartbeat(body: DoneRequest):
    """Keeps a lease alive through long stretches with nothing to cache (decided positions)."""
    await asyncio.to_thread(service.put_rows, body.gameId, body.node, [], [])
    return {"ok": True}


@app.post("/nodes/done")
async def done(body: DoneRequest):
    await asyncio.to_thread(service.done, body.gameId, body.node)
    return {"ok": True}


@app.get("/nodes/status")
async def status():
    """Queue, speed per machine and time left, for the node's status window (cached a few seconds)."""
    return await asyncio.to_thread(service.status)
