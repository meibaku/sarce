"""
Sarce Node (ADR 0010): searches games for a Sarce server over the network, with the server's own code.

    python sarce_node.py            # reads node.env next to this file

node.env holds SERVER (e.g. http://10.77.0.1:8002), TOKEN (the server's NODE_TOKEN), NODE (a name), WORKERS
(engines in parallel, one game each) and STOCKFISH_PATH. The runner (run-node.ps1) starts this, restarts it when
it stops, and downloads a new bundle when the server's version changes (exit code 3).

Built for a machine that loses power: every few positions the rows go to the server (which also renews the
lease), so after a restart the same game resumes from what was already stored, and a server that isn't up yet
is simply waited for.
"""

from __future__ import annotations

import ctypes
import io
import threading
import json
import multiprocessing as mp
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
UPDATE_EXIT = 3
FLUSH_ROWS = 8
FLUSH_S = 45
IDLE_S = 60
HEARTBEAT_S = 60
STATUS_DIR = HERE.parent / "status"  # read by status.ps1 every couple of seconds; no token in here
SERVER_POLL_S = 5
VERSION_CHECK_S = 300


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    path = HERE.parent / "node.env"
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    return env


class Gateway:
    def __init__(self, server: str, token: str, node: str) -> None:
        self.server, self.token, self.node = server.rstrip("/"), token, node

    def call(self, path: str, body: dict | None = None, timeout: float = 60):
        data = None if body is None else json.dumps({"node": self.node, **body}).encode()
        req = urllib.request.Request(
            self.server + path, data=data, method="GET" if body is None else "POST",
            headers={"X-Sarce-Node": self.token, "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.loads(res.read())

    def call_retrying(self, path: str, body: dict | None = None):
        """Retries until the server answers: after a power cut either machine may come back first."""
        wait = 5
        while True:
            try:
                return self.call(path, body)
            except urllib.error.HTTPError as exc:
                if exc.code == 401:
                    raise SystemExit("The server refused this node's token: check TOKEN in node.env") from exc
                print(f"server error {exc.code} on {path}; retrying in {wait}s", flush=True)
            except (urllib.error.URLError, OSError, TimeoutError) as exc:
                print(f"server not reachable ({exc}); retrying in {wait}s", flush=True)
            time.sleep(wait)
            wait = min(wait * 2, 120)


def write_status(name: str, data: dict) -> None:
    """
    One small JSON file per writer, replaced atomically so the status window never reads half a file. Never raises:
    on Windows a replace can fail while the window has the file open, and a full disk mustn't stop the analysis.
    """
    try:
        STATUS_DIR.mkdir(exist_ok=True)
        tmp = STATUS_DIR / f"{name}.tmp"
        tmp.write_text(json.dumps({**data, "day": time.strftime("%Y-%m-%d"), "at": time.time()}), encoding="utf-8")
        for _ in range(3):
            try:
                os.replace(tmp, STATUS_DIR / f"{name}.json")
                return
            except PermissionError:
                time.sleep(0.05)  # the window is reading it; the next snapshot will do if this one can't land
    except OSError:
        pass


def games_today(index: int) -> int:
    """This engine's count for today from its last snapshot, so a restart or an update doesn't zero the day."""
    try:
        last = json.loads((STATUS_DIR / f"engine-{index}.json").read_text(encoding="utf-8"))
        return int(last.get("gamesToday") or 0) if last.get("day") == time.strftime("%Y-%m-%d") else 0
    except (OSError, ValueError):
        return 0


class ProgressEngine:
    """The engine, noting each position it searches: `game_lines` searches decided positions without the store."""

    def __init__(self, engine, on_position) -> None:
        self.engine, self.on_position = engine, on_position

    @property
    def engine_version(self) -> str:
        return self.engine.engine_version

    def analyse(self, board, nodes: int, multipv: int):
        self.on_position(board.fen().rsplit(" ", 1)[0])
        return self.engine.analyse(board, nodes=nodes, multipv=multipv)


class RemoteStore:
    """An EvalStore (position_evals.EvalStore) over the gateway: reads from the claim's rows, writes in batches."""

    def __init__(self, cached: dict[str, dict], flush, on_get=None) -> None:
        self.rows, self.pending, self.flush, self.last = dict(cached), [], flush, time.monotonic()
        self.on_get = on_get  # called with each position's key: the engine's progress through the game

    def get(self, key: str, nodes: int) -> dict | None:
        if self.on_get:
            self.on_get(key)
        row = self.rows.get(key)
        return row if row and row.get("nodes") == nodes else None

    def put(self, row: dict) -> None:
        self.rows[row["fen_key"]] = row
        self.pending.append(row)
        if len(self.pending) >= FLUSH_ROWS or time.monotonic() - self.last > FLUSH_S:
            self.flush()


def keep_awake() -> None:
    """Windows: don't let the machine sleep while the node runs (ES_CONTINUOUS | ES_SYSTEM_REQUIRED)."""
    if sys.platform == "win32":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)


def watch_parent() -> None:
    """
    End this engine process when the node's main process is gone. On Windows a parent killed hard leaves its
    children running as orphans: they would keep an old bundle forever and double up with the next start's engines.
    """
    parent = mp.parent_process()

    def watch() -> None:
        while True:
            time.sleep(5)
            if parent is not None and not parent.is_alive():
                os._exit(0)

    threading.Thread(target=watch, daemon=True).start()


def worker(index: int, env: dict[str, str], settings_env: dict[str, str]) -> None:
    os.environ.update(settings_env)
    os.environ["STOCKFISH_PATH"] = env["STOCKFISH_PATH"]
    sys.path.insert(0, str(HERE.parent / "api"))
    import chess.pgn  # noqa: E402

    from app.services.move_classifier import MoveClassifier  # noqa: E402
    from app.services.position_evals import game_lines  # noqa: E402
    from app.services.stockfish import StockfishEngine  # noqa: E402
    from app.services.threats import evaluate_game_threats  # noqa: E402

    name = f"{env['NODE']}-{index}"
    gw = Gateway(env["SERVER"], env["TOKEN"], name)
    watch_parent()
    keep_awake()
    done_today, day, last_seconds = games_today(index), time.strftime("%Y-%m-%d"), None
    with StockfishEngine() as real_engine:
        sf_pid = real_engine.pid  # the monitor reads this Stockfish's CPU and memory along with the worker's
        while True:
            if time.strftime("%Y-%m-%d") != day:  # midnight, even while idle
                done_today, day = 0, time.strftime("%Y-%m-%d")
            write_status(f"engine-{index}", {"engine": index, "state": "asking", "gamesToday": done_today, "lastGameSeconds": last_seconds, "pid": os.getpid(), "sfPid": sf_pid})
            job = gw.call_retrying("/nodes/claim", {}).get("job")
            if not job:
                write_status(f"engine-{index}", {"engine": index, "state": "idle", "gamesToday": done_today, "lastGameSeconds": last_seconds, "pid": os.getpid(), "sfPid": sf_pid})
                time.sleep(IDLE_S)
                continue
            game_id, started, wall_start = job["gameId"], time.monotonic(), time.time()
            progress = {"positions": 0, "threats": 0, "last": 0.0, "seen": set()}
            total = max(1, job["pgn"].count(".") * 2)  # a rough count until the PGN is read below

            def report(phase: str) -> None:
                if time.monotonic() - progress["last"] < 1:  # at most once a second
                    return
                progress["last"] = time.monotonic()
                write_status(f"engine-{index}", {
                    "engine": index, "state": phase, "gameId": game_id, "done": progress["positions"], "total": total,
                    "threatsDone": progress["threats"], "startedAt": wall_start, "progressAt": progress.get("at", wall_start),
                    "gamesToday": done_today, "lastGameSeconds": last_seconds, "pid": os.getpid(), "sfPid": sf_pid,
                })

            def seen_position(key: str) -> None:
                if key not in progress["seen"]:  # a position looked up and then searched counts once
                    progress["seen"].add(key)
                    progress["positions"] = len(progress["seen"])
                    progress["at"] = time.time()
                    report("searching")

            def seen_threat(key: str) -> None:
                progress["threats"] += 1
                progress["at"] = time.time()
                report("threats")

            engine = ProgressEngine(real_engine, seen_position)

            evals = RemoteStore(job["evals"], lambda: None, seen_position)
            threats = RemoteStore(job["threats"], lambda: None, seen_threat)

            def flush() -> None:
                if evals.pending or threats.pending:
                    gw.call_retrying("/nodes/rows", {"gameId": game_id, "evals": evals.pending, "threats": threats.pending})
                evals.pending, threats.pending = [], []
                evals.last = threats.last = time.monotonic()

            evals.flush = threats.flush = flush
            # A heartbeat on its own timer: decided positions are searched but not cached, so rows can pause for
            # longer than the lease while the worker is busy.
            stop = threading.Event()

            def beat(gid: str = game_id) -> None:
                while not stop.wait(HEARTBEAT_S):
                    try:
                        gw.call("/nodes/heartbeat", {"gameId": gid}, timeout=20)
                    except Exception:
                        pass

            threading.Thread(target=beat, daemon=True).start()
            game = chess.pgn.read_game(io.StringIO(job["pgn"]))
            if game is None:
                gw.call_retrying("/nodes/done", {"gameId": game_id})
                continue
            try:
                board, moves = game.board(), list(game.mainline_moves())
                total = len(moves) + 1
                lines = game_lines(board, moves, engine, evals)
                classified = MoveClassifier().classify_game(board, moves, job["userColor"], lines=lines)
                evaluate_game_threats(board, moves, job["userColor"], classified, real_engine, threats)
                flush()
            finally:
                stop.set()
            # Positions searched or looked up: the same measure the server's own analysis reports.
            gw.call_retrying("/nodes/done", {"gameId": game_id, "positions": progress["positions"]})
            last_seconds = round(time.monotonic() - started)
            done_today += 1
            print(f"[{name}] {game_id}: {len(moves)} plies in {last_seconds}s", flush=True)


def status_shortcut() -> None:
    """A "Sarce Node status" launcher on the shared Desktop, so anyone at the machine can open the live window."""
    if sys.platform != "win32":
        return
    try:
        desktop = Path(os.environ.get("PUBLIC", r"C:\Users\Public")) / "Desktop"
        launcher = desktop / "Sarce Node status.cmd"
        script = HERE / "status.ps1"
        launcher.write_text(f'@echo off\r\npowershell -NoProfile -ExecutionPolicy Bypass -File "{script}"\r\n', encoding="ascii")
    except OSError:
        pass  # no shared Desktop: run node\status.ps1 directly


def main() -> int:
    env = load_env()
    gw = Gateway(env["SERVER"], env["TOKEN"], env["NODE"])
    config = gw.call_retrying("/nodes/config")
    local = (HERE.parent / "VERSION").read_text(encoding="utf-8").strip() if (HERE.parent / "VERSION").exists() else ""
    if not config.get("ready", True):
        print("the server doesn't read the engine cache (POSITION_EVALS_ENABLED is off), so there's nothing useful to do; waiting", flush=True)
        time.sleep(600)
        return 0
    if config["version"] != local:
        print(f"server runs {config['version']}, this node has {local or 'nothing'}: updating", flush=True)
        return UPDATE_EXIT
    workers = max(1, int(env.get("WORKERS", "3")))
    print(f"Sarce Node {env['NODE']}: {workers} engines, server {env['SERVER']}, bundle {local}", flush=True)
    keep_awake()
    status_shortcut()
    for old in STATUS_DIR.glob("engine-*.json") if STATUS_DIR.exists() else []:
        try:
            if int(old.stem.split("-")[1]) >= workers:
                old.unlink()  # engines from a larger WORKERS shouldn't linger in the window
        except (OSError, ValueError):
            pass
    procs = [mp.Process(target=worker, args=(i, env, config["settings"]), daemon=True) for i in range(workers)]
    for p in procs:
        p.start()
    last_check, last_ok = time.monotonic(), None
    sys.path.insert(0, str(HERE.parent / "api"))
    from app.services.procstats import Sampler  # noqa: E402  (from the bundle, like the workers' imports)

    sampler, started_at = Sampler(), time.time()
    while True:
        time.sleep(SERVER_POLL_S)
        # This machine and its engines for the analysis monitor: CPU and memory per worker plus its Stockfish.
        try:
            engines = []
            for path in sorted(STATUS_DIR.glob("engine-*.json")):
                try:
                    e = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                e["cpu"], e["rssMb"] = sampler.process(e.get("pid"), e.get("sfPid"))
                engines.append(e)
            gw.call("/nodes/report", {"machine": sampler.machine(), "engines": engines, "bundle": local, "startedAt": started_at}, timeout=10)
        except Exception:
            pass  # the monitor is optional; the work goes on
        # The laptop's picture of the whole queue, for the status window (the gateway caches it).
        try:
            summary = gw.call("/nodes/status", timeout=10)
            last_ok = time.time()
            write_status("server", {"ok": True, "lastOk": last_ok, "server": env["SERVER"], "node": env["NODE"], "bundle": local, "engines": workers, **summary})
        except Exception as exc:
            write_status("server", {"ok": False, "lastOk": last_ok, "server": env["SERVER"], "node": env["NODE"], "bundle": local, "engines": workers, "error": str(exc)[:120]})
        if time.monotonic() - last_check >= VERSION_CHECK_S:
            last_check = time.monotonic()
            try:
                if gw.call("/nodes/config")["version"] != local:
                    print("the server was updated: restarting with the new bundle", flush=True)
                    for p in procs:
                        p.terminate()
                    return UPDATE_EXIT
            except Exception:
                pass  # server down: the workers wait for it themselves
        for i, p in enumerate(procs):
            if not p.is_alive():
                procs[i] = mp.Process(target=worker, args=(i, env, config["settings"]), daemon=True)
                procs[i].start()


if __name__ == "__main__":
    mp.freeze_support()
    sys.exit(main())
