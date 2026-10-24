"""
Paired Sarce Nodes (ADR 0010): leases, cached rows and the code bundle the node gateway serves.

A node leases one pending game at a time, searches its positions with the server's own code and sends the engine
rows back in batches; they go straight into the shared caches (`position_evals`, `position_threats`). The server's
analysis skips games under a live lease and, once a node is done, finds every position cached. A lease without a
heartbeat for LEASE_S (a power cut) returns its game to the pool; the same node re-leases it on restart and finds
its earlier rows already stored.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import zipfile
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import chess
import chess.pgn

from app.config import settings
from app.db.supabase import get_supabase
from app.services.position_evals import fen_key
from app.services.threats import THREAT_NODES

TABLE = "node_leases"
LEASE_S = 300  # no heartbeat for this long and the game goes back to the pool
CHUNK = 60  # keys per `in` filter
API_DIR = Path(__file__).resolve().parents[2]  # apps/api
NODE_DIR = API_DIR.parent / "node"  # apps/node
# The settings a node must mirror so its searches are the server's (sent with /config, applied before import).
MIRRORED = ("analysis_nodes", "analysis_multipv", "analysis_multipv_cap", "safe_set_tol")


def now() -> datetime:
    return datetime.now(timezone.utc)


def token_ok(given: str | None) -> bool:
    """Constant-time check of the pairing token; no token configured means no node is accepted."""
    expected = settings.node_token
    return bool(expected) and bool(given) and hmac.compare_digest(given.encode(), expected.encode())


def live_leases() -> set[str]:
    """Games a node is searching right now (heartbeat within LEASE_S, not done): the server leaves them alone."""
    cutoff = (now() - timedelta(seconds=LEASE_S)).isoformat()
    rows = get_supabase().table(TABLE).select("game_id").is_("done_at", "null").gt("heartbeat_at", cutoff).execute().data or []
    return {r["game_id"] for r in rows}


def position_keys(pgn_text: str) -> list[str]:
    """Every mainline position's cache key, start included (what `game_lines` searches)."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        return []
    board, keys = game.board(), []
    keys.append(fen_key(board))
    for move in game.mainline_moves():
        board.push(move)
        keys.append(fen_key(board))
    return keys


def cached_rows(table: str, keys: list[str], nodes: int) -> dict[str, dict]:
    out: dict[str, dict] = {}
    unique = sorted(set(keys))
    for start in range(0, len(unique), CHUNK):
        for row in get_supabase().table(table).select("*").in_("fen_key", unique[start : start + CHUNK]).eq("nodes", nodes).execute().data or []:
            out[row["fen_key"]] = row
    return out


class NodeService:
    def config(self) -> dict:
        """What a node needs before it starts: the bundle version and the settings its searches must use."""
        return {
            "version": bundle()[1],
            "stockfish": "18",
            "settings": {name.upper(): str(getattr(settings, name)) for name in MIRRORED},
            "threatNodes": THREAT_NODES,
            "leaseSeconds": LEASE_S,
        }

    def claim(self, node: str) -> dict | None:
        """
        This node's unfinished game if it still has one (a restart after a power cut), else the newest pending game
        nobody is searching. Returns the game and the rows already cached for it, so finished positions aren't redone.
        """
        sb = get_supabase()
        mine = sb.table(TABLE).select("game_id").eq("node", node).is_("done_at", "null").execute().data or []
        game = None
        for lease in mine:
            rows = sb.table("games").select("id, pgn, user_color, analysis_status").eq("id", lease["game_id"]).limit(1).execute().data or []
            if rows and rows[0]["analysis_status"] == "pending":
                game = rows[0]
                break
            sb.table(TABLE).update({"done_at": now().isoformat()}).eq("game_id", lease["game_id"]).execute()
        if game is None:
            busy = live_leases()
            done = {r["game_id"] for r in sb.table(TABLE).select("game_id").not_.is_("done_at", "null").execute().data or []}
            candidates = (
                sb.table("games").select("id, pgn, user_color, analysis_status").eq("analysis_status", "pending")
                .order("played_at", desc=True).limit(50).execute().data
                or []
            )
            game = next((g for g in candidates if g["id"] not in busy and g["id"] not in done and g.get("pgn")), None)
            if game is None:
                return None
        stamp = now().isoformat()
        sb.table(TABLE).upsert(
            {"game_id": game["id"], "node": node, "leased_at": stamp, "heartbeat_at": stamp, "done_at": None},
            on_conflict="game_id",
        ).execute()
        keys = position_keys(game["pgn"])
        return {
            "gameId": game["id"],
            "pgn": game["pgn"],
            "userColor": game.get("user_color") or "white",
            "evals": cached_rows("position_evals", keys, settings.analysis_nodes),
            "threats": cached_rows("position_threats", keys, THREAT_NODES),
        }

    def put_rows(self, game_id: str, node: str, evals: list[dict], threats: list[dict]) -> int:
        """Stores a batch of engine rows (also the lease's heartbeat). Rows at other node counts are refused."""
        sb = get_supabase()
        good_evals = [r for r in evals if r.get("nodes") == settings.analysis_nodes and r.get("fen_key") and isinstance(r.get("lines"), list)]
        good_threats = [r for r in threats if r.get("nodes") == THREAT_NODES and r.get("fen_key") and r.get("threat_uci")]
        if good_evals:
            sb.table("position_evals").upsert(good_evals, on_conflict="fen_key,nodes").execute()
        if good_threats:
            sb.table("position_threats").upsert(good_threats, on_conflict="fen_key,nodes").execute()
        lease = sb.table(TABLE).select("positions").eq("game_id", game_id).eq("node", node).limit(1).execute().data or []
        if lease:
            sb.table(TABLE).update(
                {"heartbeat_at": now().isoformat(), "positions": lease[0]["positions"] + len(good_evals)}
            ).eq("game_id", game_id).execute()
        return len(good_evals) + len(good_threats)

    def done(self, game_id: str, node: str) -> None:
        """The node has searched every position; the server's analysis will now find them all cached."""
        get_supabase().table(TABLE).update({"done_at": now().isoformat(), "heartbeat_at": now().isoformat()}).eq("game_id", game_id).eq("node", node).execute()

    def status(self) -> list[dict]:
        """Per node: games finished in the last hour and whether it's searching now (for Settings)."""
        since = (now() - timedelta(hours=1)).isoformat()
        rows = get_supabase().table(TABLE).select("node, done_at, heartbeat_at").gt("heartbeat_at", since).execute().data or []
        out: dict[str, dict] = {}
        for r in rows:
            entry = out.setdefault(r["node"], {"node": r["node"], "gamesLastHour": 0, "active": False})
            entry["gamesLastHour"] += 1 if r.get("done_at") else 0
            entry["active"] = entry["active"] or not r.get("done_at")
        return sorted(out.values(), key=lambda e: e["node"])


@lru_cache(maxsize=1)
def bundle() -> tuple[bytes, str]:
    """The code a node runs (apps/api/app, apps/node, the node requirements) as a zip, and its version hash."""
    files: list[tuple[str, Path]] = []
    for path in sorted((API_DIR / "app").rglob("*.py")):
        files.append((f"api/{path.relative_to(API_DIR).as_posix()}", path))
    for path in sorted(NODE_DIR.glob("*")):
        if path.is_file():
            files.append((f"node/{path.name}", path))
    digest = hashlib.sha256()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, path in files:
            data = path.read_bytes()
            digest.update(name.encode() + b"\0" + data)
            zf.writestr(name, data)
    version = digest.hexdigest()[:12]
    with zipfile.ZipFile(buffer, "a") as zf:
        zf.writestr("VERSION", version)
    return buffer.getvalue(), version
