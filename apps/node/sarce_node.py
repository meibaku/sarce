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


class RemoteStore:
    """An EvalStore (position_evals.EvalStore) over the gateway: reads from the claim's rows, writes in batches."""

    def __init__(self, cached: dict[str, dict], flush) -> None:
        self.rows, self.pending, self.flush, self.last = dict(cached), [], flush, time.monotonic()

    def get(self, key: str, nodes: int) -> dict | None:
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
    keep_awake()
    with StockfishEngine() as engine:
        while True:
            job = gw.call_retrying("/nodes/claim", {}).get("job")
            if not job:
                time.sleep(IDLE_S)
                continue
            game_id, started = job["gameId"], time.monotonic()
            evals = RemoteStore(job["evals"], lambda: None)
            threats = RemoteStore(job["threats"], lambda: None)

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
                lines = game_lines(board, moves, engine, evals)
                classified = MoveClassifier().classify_game(board, moves, job["userColor"], lines=lines)
                evaluate_game_threats(board, moves, job["userColor"], classified, engine, threats)
                flush()
            finally:
                stop.set()
            gw.call_retrying("/nodes/done", {"gameId": game_id})
            print(f"[{name}] {game_id}: {len(moves)} plies in {time.monotonic() - started:.0f}s", flush=True)


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
    procs = [mp.Process(target=worker, args=(i, env, config["settings"]), daemon=True) for i in range(workers)]
    for p in procs:
        p.start()
    while True:
        time.sleep(300)
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
