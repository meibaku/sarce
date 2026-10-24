"""
Analysis monitor (dev mode): every machine and engine at work, what happened, and how fast.

Writers:
- the server's own analysis: `track_game` marks an analysis slot busy with a game, and a counting store reports
  its progress through the positions (`analysis.py`);
- Sarce Nodes: their main process reports machine and engine snapshots through the gateway (`/nodes/report`);
- `tick()` (every few seconds in the API) writes the server's machine snapshot, raises alerts and trims history.

Readers: `/monitor/*` (routers/monitor.py) and the web monitor page. Snapshot writes are throttled, and nothing here
may ever fail an analysis: every write is best effort.
"""

from __future__ import annotations

import contextvars
import logging
import socket
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from app.db.supabase import get_supabase
from app.services.procstats import Sampler

logger = logging.getLogger(__name__)

MACHINE = socket.gethostname().lower()  # the server's own machine name, as nodes use theirs
WRITE_S = 2.0  # at most one snapshot write per slot this often
OFFLINE_S = 45  # a machine silent this long is offline
STALL_S = 180  # an engine at the same position this long is stalled
DROP_RATIO = 0.5  # a machine's last 10 minutes below half of its 30 before is a drop
KEEP_DAYS = 30
EVENTS = "analysis_events"

current: contextvars.ContextVar[Tracker | None] = contextvars.ContextVar("analysis_tracker", default=None)
_sampler = Sampler()
_slots: dict[int, "Tracker"] = {}  # busy server slots, refreshed by every tick so a long search still shows
_slots_lock = threading.Lock()
_active_alerts: set[str] = set()
STARTED_AT = datetime.now(timezone.utc)


def now() -> datetime:
    return datetime.now(timezone.utc)


def event(kind: str, machine: str | None = MACHINE, engine: int | None = None, game_id: str | None = None, **detail) -> None:
    """Append to the event feed (best effort)."""
    try:
        get_supabase().table(EVENTS).insert({"kind": kind, "machine": machine, "engine": engine, "game_id": game_id, "detail": detail}).execute()
    except Exception:
        logger.debug("monitor event %s not written", kind, exc_info=True)


def bump(machine: str, games: int = 1, positions: int = 0) -> None:
    try:
        get_supabase().rpc("bump_throughput", {"p_machine": machine, "p_games": games, "p_positions": positions}).execute()
    except Exception:
        logger.debug("throughput not bumped", exc_info=True)


class Tracker:
    """One server analysis slot busy with a game: progress through its positions, its Stockfish's resources."""

    def __init__(self, game_id: str, slot: int) -> None:
        self.game_id, self.slot = game_id, slot
        self.done = self.total = 0
        self.state = "classifying"
        self.started = now()
        self.progress_at = self.started
        self.engine_pid: int | None = None
        self.seen: set[str] = set()
        self._last_write = 0.0

    def position(self, key: str) -> None:
        if key not in self.seen:
            self.seen.add(key)
            self.done = len(self.seen)
            self.progress_at = now()
            self.write()

    def phase(self, state: str, total: int | None = None) -> None:
        self.state = state
        if total is not None:
            self.total, self.seen, self.done = total, set(), 0
        self.write(force=True)

    def write(self, force: bool = False) -> None:
        if not force and time.monotonic() - self._last_write < WRITE_S:
            return
        self._last_write = time.monotonic()
        cpu, rss = _sampler.process(self.engine_pid)
        try:
            get_supabase().table("engine_snapshots").upsert({
                "machine": MACHINE, "engine": self.slot, "state": self.state, "game_id": self.game_id,
                "done": self.done, "total": self.total, "started_at": self.started.isoformat(),
                "progress_at": self.progress_at.isoformat(), "cpu": cpu, "rss_mb": rss, "updated_at": now().isoformat(),
            }, on_conflict="machine,engine").execute()
        except Exception:
            logger.debug("engine snapshot not written", exc_info=True)


@contextmanager
def track_game(game_id: str):
    """Mark a server analysis slot busy with this game for the duration (the context reaches worker threads)."""
    with _slots_lock:
        slot = next(i for i in range(1000) if i not in _slots)
        tracker = Tracker(game_id, slot)
        _slots[slot] = tracker
    token = current.set(tracker)
    background(tracker.write, True)  # never a database round trip on the API's event loop
    try:
        yield tracker
    finally:
        current.reset(token)
        with _slots_lock:
            _slots.pop(slot, None)
        background(_idle, slot, int((now() - tracker.started).total_seconds()))


def background(fn, *args) -> None:
    """Run a best-effort monitor write off the caller's thread (the API's event loop must never wait on it)."""
    threading.Thread(target=fn, args=args, daemon=True).start()


def _idle(slot: int, seconds: int) -> None:
    try:
        get_supabase().table("engine_snapshots").upsert({
            "machine": MACHINE, "engine": slot, "state": "idle", "game_id": None, "done": 0, "total": 0,
            "last_game_s": seconds, "updated_at": now().isoformat(),
        }, on_conflict="machine,engine").execute()
    except Exception:
        pass


class CountingStore:
    """Wraps an EvalStore: each position looked up counts towards the current game's progress."""

    def __init__(self, store) -> None:
        self.store = store

    def get(self, key: str, nodes: int):
        tracker = current.get()
        if tracker:
            tracker.position(key)
        return self.store.get(key, nodes)

    def put(self, row: dict) -> None:
        self.store.put(row)


class CountingEngine:
    """Wraps the engine: positions searched without a store lookup (decided ones) count towards progress too."""

    def __init__(self, engine) -> None:
        self.engine = engine

    @property
    def engine_version(self) -> str:
        return self.engine.engine_version

    def analyse(self, board, nodes: int, multipv: int):
        tracker = current.get()
        if tracker:
            tracker.position(board.fen().rsplit(" ", 1)[0])
        return self.engine.analyse(board, nodes=nodes, multipv=multipv)


def engine_started(pid: int | None) -> None:
    """Called when a Stockfish process opens inside a tracked game, so its CPU and memory can be read."""
    tracker = current.get()
    if tracker:
        tracker.engine_pid = pid


# --- the API's tick: the server's machine snapshot, alerts, retention ---------------------------------------------

def tick(engines: int) -> None:
    with _slots_lock:
        busy = list(_slots.values())
    for tracker in busy:
        tracker.write(force=True)  # fresh CPU and memory, and proof of life during a long search
    sb = get_supabase()
    stats = _sampler.machine()
    sb.table("machine_snapshots").upsert({
        "machine": MACHINE, "role": "server", "cpu": stats["cpu"], "mem_used": stats["memUsed"], "mem_total_gb": stats["memTotalGb"],
        "uptime_s": stats["uptimeS"], "process_started_at": STARTED_AT.isoformat(), "engines": engines, "updated_at": now().isoformat(),
    }, on_conflict="machine").execute()
    for key, (kind, machine, detail) in alerts().items():
        if key not in _active_alerts:
            _active_alerts.add(key)
            event(kind, machine=machine, **detail)
    current_keys = set(alerts())
    for key in list(_active_alerts):
        if key not in current_keys:
            _active_alerts.discard(key)
            event("recovered", machine=key.split("|", 1)[1], cleared=key.split("|", 1)[0])


def trim() -> None:
    cutoff = (now() - timedelta(days=KEEP_DAYS)).isoformat()
    sb = get_supabase()
    sb.table(EVENTS).delete().lt("at", cutoff).execute()
    sb.table("analysis_throughput").delete().lt("minute", cutoff).execute()


def alerts() -> dict[str, tuple[str, str, dict]]:
    """Live problems keyed "kind|machine": offline machines, stalled engines, rate drops."""
    sb = get_supabase()
    out: dict[str, tuple[str, str, dict]] = {}
    t = now()
    for m in sb.table("machine_snapshots").select("machine, updated_at").execute().data or []:
        silent = (t - datetime.fromisoformat(m["updated_at"])).total_seconds()
        if silent > OFFLINE_S:
            out[f"offline|{m['machine']}"] = ("offline", m["machine"], {"silentS": int(silent)})
    for e in sb.table("engine_snapshots").select("machine, engine, state, progress_at, updated_at").neq("state", "idle").execute().data or []:
        if e.get("progress_at") and (t - datetime.fromisoformat(e["updated_at"])).total_seconds() < OFFLINE_S:
            stuck = (t - datetime.fromisoformat(e["progress_at"])).total_seconds()
            if stuck > STALL_S:
                out[f"stalled-{e['engine']}|{e['machine']}"] = ("stalled", e["machine"], {"engine": e["engine"], "stuckS": int(stuck)})
    since = (t - timedelta(minutes=40)).isoformat()
    rows = sb.table("analysis_throughput").select("minute, machine, games").gt("minute", since).execute().data or []
    recent_cut = (t - timedelta(minutes=10)).isoformat()
    by_machine: dict[str, list[int]] = {}
    for r in rows:
        bucket = by_machine.setdefault(r["machine"], [0, 0])
        bucket[0 if r["minute"] >= recent_cut else 1] += r["games"]
    for machine, (recent, before) in by_machine.items():
        before_rate, recent_rate = before / 30, recent / 10
        if before >= 6 and recent_rate < before_rate * DROP_RATIO:
            out[f"drop|{machine}"] = ("rate_drop", machine, {"perHourNow": round(recent_rate * 60), "perHourBefore": round(before_rate * 60)})
    return out


# --- reads for /monitor -------------------------------------------------------------------------------------------

def snapshot() -> dict:
    """Everything the monitor page shows at once: queue, machines with their engines and games, alerts."""
    sb = get_supabase()

    def count(status: str) -> int:
        return sb.table("games").select("id", count="exact").eq("analysis_status", status).limit(1).execute().count or 0

    queue = {s: count(s) for s in ("pending", "processing", "complete", "failed")}
    t = now()
    hour_ago = (t - timedelta(hours=1)).isoformat()
    per_hour = sb.table("games").select("id", count="exact").gt("analysed_at", hour_ago).limit(1).execute().count or 0
    machines = sb.table("machine_snapshots").select("*").order("machine").execute().data or []
    engines = sb.table("engine_snapshots").select("*").order("machine").order("engine").execute().data or []
    game_ids = sorted({e["game_id"] for e in engines if e.get("game_id")})
    games = {
        g["id"]: g
        for g in (sb.table("games").select("id, opponent, opponent_rating, user_color, time_control, played_at, source").in_("id", game_ids).execute().data if game_ids else [])
        or []
    }
    rates = {r["machine"]: r for r in _rates(t)}
    out_machines = []
    for m in machines:
        silent = (t - datetime.fromisoformat(m["updated_at"])).total_seconds()
        mine = []
        for e in engines:
            if e["machine"] != m["machine"]:
                continue
            fresh = (t - datetime.fromisoformat(e["updated_at"])).total_seconds() < max(OFFLINE_S, 120)
            if not fresh and e["state"] == "idle":
                continue
            elapsed = (t - datetime.fromisoformat(e["started_at"])).total_seconds() if e.get("started_at") and e["state"] != "idle" else None
            eta = elapsed / e["done"] * (e["total"] - e["done"]) if elapsed and e.get("done") and e.get("total", 0) > e["done"] else None
            mine.append({**e, "game": games.get(e.get("game_id") or ""), "elapsedS": None if elapsed is None else int(elapsed), "etaS": None if eta is None else int(eta), "stale": not fresh})
        out_machines.append({**m, "online": silent < OFFLINE_S, "silentS": int(silent), "engineRows": mine, "rate": rates.get(m["machine"])})
    active = alerts()
    return {
        "at": t.isoformat(),
        "queue": {**queue, "total": sum(queue.values())},
        "perHour": per_hour,
        "etaHours": round(queue["pending"] / per_hour, 1) if per_hour else None,
        "machines": out_machines,
        "alerts": [{"key": k, "kind": kind, "machine": machine, **detail} for k, (kind, machine, detail) in active.items()],
    }


def _rates(t: datetime) -> list[dict]:
    """Games per hour per machine: the last 10 minutes and the last hour, from the throughput series."""
    rows = get_supabase().table("analysis_throughput").select("minute, machine, games, positions").gt("minute", (t - timedelta(hours=1)).isoformat()).execute().data or []
    cut = (t - timedelta(minutes=10)).isoformat()
    out: dict[str, dict] = {}
    for r in rows:
        m = out.setdefault(r["machine"], {"machine": r["machine"], "lastHour": 0, "last10": 0, "positionsLastHour": 0})
        m["lastHour"] += r["games"]
        m["positionsLastHour"] += r["positions"]
        m["last10"] += r["games"] if r["minute"] >= cut else 0
    for m in out.values():
        m["perHourNow"] = m["last10"] * 6
    return list(out.values())


def history(hours: int = 24, bucket_min: int = 10) -> dict:
    """Games per machine in `bucket_min`-minute buckets over the last `hours`, plus the alerts in that window."""
    t = now()
    since = t - timedelta(hours=hours)
    rows: list[dict] = []
    sb = get_supabase()
    while True:
        batch = sb.table("analysis_throughput").select("minute, machine, games").gt("minute", since.isoformat()).order("minute").range(len(rows), len(rows) + 999).execute().data or []
        rows += batch
        if len(batch) < 1000:
            break
    buckets: dict[str, dict[str, int]] = {}
    for r in rows:
        minute = datetime.fromisoformat(r["minute"])
        start = minute - timedelta(minutes=minute.minute % bucket_min)
        key = start.replace(second=0, microsecond=0).isoformat()
        buckets.setdefault(r["machine"], {}).setdefault(key, 0)
        buckets[r["machine"]][key] += r["games"]
    marks = (
        sb.table(EVENTS).select("at, kind, machine, detail").gt("at", since.isoformat())
        .in_("kind", ["offline", "stalled", "rate_drop", "recovered", "node_started", "updated"]).order("at").execute().data
        or []
    )
    return {"from": since.isoformat(), "to": t.isoformat(), "bucketMin": bucket_min, "series": buckets, "marks": marks}


def events(limit: int = 100, machine: str | None = None) -> list[dict]:
    q = get_supabase().table(EVENTS).select("*").order("at", desc=True).limit(min(limit, 500))
    if machine:
        q = q.eq("machine", machine)
    return q.execute().data or []


def game_finished(game_id: str, seconds: int, positions: int, moves: int | None) -> None:
    """A server analysis ended: counted for this machine, unless a node had searched it (then the node got the count)."""
    if searched_by_node(game_id):
        event("finished_from_node", game_id=game_id, seconds=seconds)
    else:
        bump(MACHINE, 1, positions)
        event("game_done", game_id=game_id, seconds=seconds, moves=moves, positions=positions)


def searched_by_node(game_id: str) -> bool:
    try:
        rows = get_supabase().table("node_leases").select("done_at").eq("game_id", game_id).limit(1).execute().data or []
        return bool(rows and rows[0].get("done_at"))
    except Exception:
        return False


def node_report(machine: str, stats: dict, engines: list[dict], bundle: str | None, started_epoch: float | None) -> None:
    """A node's machine and engine snapshots (through the gateway); a new process start is logged as a restart."""
    sb = get_supabase()
    started_at = _iso(started_epoch)
    previous = sb.table("machine_snapshots").select("process_started_at").eq("machine", machine).limit(1).execute().data or []
    known = previous[0].get("process_started_at") if previous else None
    if started_at and (not known or abs((datetime.fromisoformat(known) - datetime.fromisoformat(started_at)).total_seconds()) > 1):
        event("node_started", machine=machine, bundle=bundle, uptimeS=stats.get("uptimeS"))
    sb.table("machine_snapshots").upsert({
        "machine": machine, "role": "node", "cpu": stats.get("cpu"), "mem_used": stats.get("memUsed"), "mem_total_gb": stats.get("memTotalGb"),
        "uptime_s": stats.get("uptimeS"), "process_started_at": started_at, "bundle": bundle, "engines": len(engines), "updated_at": now().isoformat(),
    }, on_conflict="machine").execute()
    rows = []
    for e in engines:
        rows.append({
            "machine": machine, "engine": int(e["engine"]), "state": str(e.get("state") or "unknown")[:20], "game_id": e.get("gameId"),
            "done": int(e.get("done") or 0), "total": int(e.get("total") or 0),
            "started_at": _ago(e.get("startedAgo")), "progress_at": _ago(e.get("progressAgo")),
            "cpu": e.get("cpu"), "rss_mb": e.get("rssMb"), "games_today": int(e.get("gamesToday") or 0),
            "last_game_s": e.get("lastGameSeconds"), "updated_at": now().isoformat(),
        })
    if rows:
        sb.table("engine_snapshots").upsert(rows, on_conflict="machine,engine").execute()


def _ago(seconds) -> str | None:
    """A node's "this long ago" on the server's clock (node clocks drift when offline)."""
    return None if seconds is None else (now() - timedelta(seconds=float(seconds))).isoformat()


def _iso(epoch) -> str | None:
    return None if not epoch else datetime.fromtimestamp(float(epoch), tz=timezone.utc).isoformat()

