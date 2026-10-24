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
MIRRORED = ("analysis_nodes", "analysis_multipv", "analysis_multipv_cap", "safe_set_tol", "ep_decided_low", "ep_decided_high")


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
        """What a node needs before it starts: the version (code and settings) and the settings to search with."""
        return {
            "version": bundle()[1],
            # False when the server ignores the engine caches (POSITION_EVALS_ENABLED off): nodes then wait.
            "ready": settings.position_evals_enabled,
            "stockfish": "18",
            "settings": {name.upper(): str(getattr(settings, name)) for name in MIRRORED},
            "threatNodes": THREAT_NODES,
            "leaseSeconds": LEASE_S,
        }

    def claim(self, node: str) -> dict | None:
        """
        This node's unfinished game if it still has one (a restart after a power cut), else the newest pending game
        nobody is searching, taken atomically in the database (`claim_node_game`), with the rows already cached for
        it, so finished positions aren't redone. None when there's nothing to do or the server doesn't read the
        cache (POSITION_EVALS_ENABLED off: a node's work would be wasted).
        """
        if not settings.position_evals_enabled:
            return None
        sb = get_supabase()
        game_id = sb.rpc("claim_node_game", {"p_node": node, "p_lease_s": LEASE_S}).execute().data
        if not game_id:
            return None
        rows = sb.table("games").select("id, pgn, user_color").eq("id", game_id).limit(1).execute().data or []
        if not rows or not rows[0].get("pgn"):
            self.done(game_id, node)
            return None
        game = rows[0]
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

    def finished_games(self) -> list[str]:
        """Games a node has searched that the server hasn't analysed yet (the main API's finisher picks them up)."""
        sb = get_supabase()
        done = [r["game_id"] for r in sb.table(TABLE).select("game_id").not_.is_("done_at", "null").order("done_at", desc=True).limit(200).execute().data or []]
        if not done:
            return []
        pending = sb.table("games").select("id").in_("id", done).eq("analysis_status", "pending").execute().data or []
        ids = {r["id"] for r in pending}
        return [g for g in done if g in ids]

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


def signature(data: bytes) -> str:
    """HMAC-SHA256 of the bundle with the pairing token: the node checks it before running anything it downloaded."""
    return hmac.new(settings.node_token.encode(), data, hashlib.sha256).hexdigest()


@lru_cache(maxsize=1)
def bundle() -> tuple[bytes, str]:
    """
    The code a node runs (apps/api/app, apps/node) as a zip, and a version hash over the code and the mirrored
    settings, so changing ANALYSIS_NODES (say) also makes every node restart with the new value.
    """
    files: list[tuple[str, Path]] = []
    for path in sorted((API_DIR / "app").rglob("*.py")):
        files.append((f"api/{path.relative_to(API_DIR).as_posix()}", path))
    for path in sorted(NODE_DIR.glob("*")):
        if path.is_file():
            files.append((f"node/{path.name}", path))
    digest = hashlib.sha256(repr({name: getattr(settings, name) for name in MIRRORED}).encode())
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
