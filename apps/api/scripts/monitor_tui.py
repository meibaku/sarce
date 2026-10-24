"""
Sarce analysis monitor in the terminal (dev tool): the same data as the web page `/dev/monitor`.

    pip install -r requirements-monitor.txt
    python scripts/monitor_tui.py [--api http://127.0.0.1:8001] [--token <supabase access token>]

Textual redraws only what changed, so nothing flickers. It reads the API's `/monitor/*` routes over plain HTTP
(stdlib only, besides Textual); signed-in deployments need a token for a user in MONITOR_OPERATORS.

Keys: arrows pick an engine (its recent events show on the right), m cycles the event feed's machine filter,
p pauses, r refreshes now, q quits.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from datetime import datetime, timezone

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import DataTable, Footer, Header, Sparkline, Static

SNAPSHOT_S = 2.0  # the live part; history and events change slowly
SLOW_S = 10.0
BAR = 12

MACHINE_COLS = [("machine", "Machine"), ("role", "Role"), ("state", "State"), ("cpu", "CPU"), ("ram", "RAM"),
                ("now", "Games/h now"), ("hour", "Last hour"), ("pos", "Positions/h"), ("up", "Up"), ("bundle", "Bundle")]
ENGINE_COLS = [("engine", "Engine"), ("state", "State"), ("game", "Game"), ("progress", "Positions"), ("elapsed", "Elapsed"),
               ("eta", "ETA"), ("cpu", "CPU"), ("mem", "Memory"), ("today", "Today · last")]
ALERT_KINDS = {"offline", "stalled", "rate_drop", "game_failed"}
GOOD_KINDS = {"recovered", "node_started", "updated"}
CLEARED = {"offline": "back online", "stalled": "progressing again", "drop": "speed back"}


def dur(seconds: float | None) -> str:
    if seconds is None:
        return "–"
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60:02d}s"
    if s < 86400 * 2:
        return f"{s // 3600}h {s % 3600 // 60:02d}m"
    return f"{s / 86400:.1f}d"


def bar(frac: float, width: int = BAR) -> Text:
    filled = round(max(0.0, min(1.0, frac)) * width)
    return Text.assemble(("█" * filled, "dodger_blue2"), ("░" * (width - filled), "grey35"))


def pct(value: float | None) -> str:
    return "–" if value is None else f"{value:.0f}%"


def clock(iso: str | None) -> str:
    if not iso:
        return "–"
    return datetime.fromisoformat(iso).astimezone().strftime("%H:%M:%S")


def alert_text(a: dict) -> str:
    machine = a.get("machine", "")
    if a["kind"] == "offline":
        return f"{machine} silent for {dur(a.get('silentS'))}"
    if a["kind"] == "stalled":
        return f"{machine} #{a.get('engine')} no progress for {dur(a.get('stuckS'))}"
    if a["kind"] == "rate_drop":
        return f"{machine} slowed to {a.get('perHourNow')}/h from {a.get('perHourBefore')}/h"
    return f"{machine} {a['kind']}"


class Api:
    def __init__(self, base: str, token: str | None) -> None:
        self.base = base.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}

    def get(self, path: str) -> dict:
        req = urllib.request.Request(self.base + path, headers=self.headers)
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.loads(res.read())


class MonitorApp(App):
    TITLE = "Sarce · analysis monitor"
    CSS = """
    #kpis { height: 3; padding: 0 1; border-bottom: solid $panel; }
    #alerts { height: auto; padding: 0 1; color: $warning; display: none; }
    #machines { height: auto; max-height: 8; }
    #engines { height: auto; max-height: 50%; }
    #lower { height: 1fr; min-height: 12; }
    #throughput { width: 1fr; border: round $panel; padding: 0 1; }
    #throughput Sparkline { height: 2; margin-bottom: 1; }
    #side { width: 1fr; border: round $panel; padding: 0 1; }
    """
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("m", "cycle_machine", "Events: machine"),
        Binding("p", "toggle_pause", "Pause"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self, api: Api) -> None:
        super().__init__()
        self.api = api
        self.snap: dict | None = None
        self.events: list[dict] = []
        self.paused = False
        self.problem: str | None = None
        self.machine_filter: str | None = None
        self.selected: str | None = None  # "machine:engine"
        self.charts: dict[str, tuple[Static, Sparkline]] = {}  # by machine; hostnames aren't valid widget ids

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("Connecting…", id="kpis")
        yield Static(id="alerts")
        yield DataTable(id="machines", cursor_type="none", zebra_stripes=False)
        yield DataTable(id="engines", cursor_type="row")
        with Horizontal(id="lower"):
            yield VerticalScroll(Static("Games per 10 min · last 24 h", classes="title"), id="throughput")
            with Vertical(id="side"):
                yield Static(id="side-title")
                yield VerticalScroll(Static(id="side-body"))
        yield Footer()

    def on_mount(self) -> None:
        for table_id, cols in (("#machines", MACHINE_COLS), ("#engines", ENGINE_COLS)):
            table = self.query_one(table_id, DataTable)
            for key, label in cols:
                table.add_column(label, key=key)
        self.action_refresh()
        self.set_interval(SNAPSHOT_S, self._tick_fast)
        self.set_interval(SLOW_S, self._tick_slow)

    # Fetching: in worker threads, so a slow API never freezes the screen.
    def _tick_fast(self) -> None:
        if not self.paused:
            self.run_worker(self._fetch_snapshot, thread=True, exclusive=True, group="snap")

    def _tick_slow(self) -> None:
        if not self.paused:
            self.run_worker(self._fetch_slow, thread=True, exclusive=True, group="slow")

    def _fetch_snapshot(self) -> None:
        try:
            snap = self.api.get("/monitor/snapshot")
        except Exception as exc:  # shown in the header line; the last snapshot stays up
            self.call_from_thread(self._set_problem, f"API not answering: {exc}"[:120])
            return
        self.call_from_thread(self._apply_snapshot, snap)

    def _fetch_slow(self) -> None:
        try:
            history = self.api.get("/monitor/history?hours=24&bucket=10")
            events = self.api.get("/monitor/events?limit=200")["events"]
        except Exception:
            return
        self.call_from_thread(self._apply_slow, history, events)

    def _set_problem(self, message: str | None) -> None:
        self.problem = message
        if self.snap:
            self._render_kpis()
        else:  # nothing to show yet: the reason, not an endless "Connecting…"
            self.query_one("#kpis", Static).update(Text(message or "Connecting…", "yellow"))

    # Rendering: cells are updated in place, so rows keep their place and the cursor stays put.
    def _apply_snapshot(self, snap: dict) -> None:
        self.snap, self.problem = snap, None
        self._render_kpis()
        alerts = snap.get("alerts") or []
        box = self.query_one("#alerts", Static)
        box.display = bool(alerts)
        box.update("\n".join(f"⚠ {alert_text(a)}" for a in alerts))
        self._sync(self.query_one("#machines", DataTable), {m["machine"]: self._machine_cells(m) for m in snap["machines"]})
        rows = {}
        for m in snap["machines"]:
            for e in m.get("engineRows", []):
                rows[f"{m['machine']}:{e['engine']}"] = self._engine_cells(m, e)
        self._sync(self.query_one("#engines", DataTable), rows)
        self._render_side()

    def _render_kpis(self) -> None:
        s = self.snap or {}
        q = s.get("queue", {})
        total, done = q.get("total") or 0, q.get("complete") or 0
        machines = s.get("machines", [])
        busy = sum(1 for m in machines for e in m.get("engineRows", []) if e["state"] != "idle" and not e.get("stale"))
        online = sum(1 for m in machines if m.get("online"))
        status = ("paused", "yellow") if self.paused else (self.problem, "yellow") if self.problem else (f"updated {clock(s.get('at'))}", "grey50")
        line1 = Text.assemble(
            ("Queue ", "bold"), bar(done / total if total else 0, 24), f" {done:,}/{total:,} ({done / total:.1%})  " if total else "  ",
            ("Left ", "bold"), f"{q.get('pending', 0):,}  ", ("Analysing ", "bold"), f"{q.get('processing', 0)}  ",
            ("Failed ", "bold"), f"{q.get('failed', 0)}",
        )
        line2 = Text.assemble(
            ("Speed ", "bold"), f"{s.get('perHour', 0)}/h  ", ("Time to go ", "bold"),
            f"{s['etaHours']} h  " if s.get("etaHours") is not None else "–  ",
            ("Machines ", "bold"), f"{online}/{len(machines)}  ", ("Engines busy ", "bold"), f"{busy}   ", status,
        )
        self.query_one("#kpis", Static).update(Text("\n").join([line1, line2]))

    @staticmethod
    def _machine_cells(m: dict) -> dict:
        rate = m.get("rate") or {}
        state = Text("online", "green") if m.get("online") else Text(f"silent {dur(m.get('silentS'))}", "yellow")
        ram = f"{m['mem_used'] * 100:.0f}% of {m['mem_total_gb']} GB" if m.get("mem_used") is not None else "–"
        return {
            "machine": Text(m["machine"], "bold"), "role": m.get("role") or "–", "state": state, "cpu": pct(m.get("cpu")),
            "ram": ram, "now": str(rate.get("perHourNow", "–")), "hour": str(rate.get("lastHour", "–")),
            "pos": f"{rate.get('positionsLastHour', 0):,}", "up": dur(m.get("uptime_s")), "bundle": (m.get("bundle") or "–")[:8],
        }

    @staticmethod
    def _engine_cells(m: dict, e: dict) -> dict:
        g = e.get("game") or {}
        busy = e["state"] != "idle" and not e.get("stale")
        state = Text("silent", "yellow") if e.get("stale") else Text(e["state"], "dodger_blue2" if busy else "grey50")
        game = f"vs {g.get('opponent') or '?'} ({g.get('opponent_rating') or '?'}) · {g.get('user_color') or '?'} · {g.get('time_control') or '?'}" if g else "–"
        frac = e["done"] / e["total"] if e.get("total") else 0
        progress = Text.assemble(bar(frac), f" {e['done']}/{e['total']}") if e.get("total") else Text("–", "grey50")
        return {
            "engine": f"{m['machine'].split('-')[-1]} #{e['engine']}", "state": state, "game": game, "progress": progress,
            "elapsed": dur(e.get("elapsedS")) if busy else "–", "eta": dur(e.get("etaS")) if busy else "–",
            "cpu": pct(e.get("cpu")), "mem": f"{e['rss_mb']:.0f} MB" if e.get("rss_mb") is not None else "–",
            "today": f"{e.get('games_today', 0)} · {dur(e.get('last_game_s'))}",
        }

    @staticmethod
    def _sync(table: DataTable, rows: dict[str, dict]) -> None:
        existing = {str(k.value) for k in table.rows}
        for key in existing - rows.keys():
            table.remove_row(key)
        for key, cells in rows.items():
            if key in existing:
                for col, value in cells.items():
                    table.update_cell(key, col, value, update_width=True)  # an idle "–" becomes a long game line
            else:
                table.add_row(*cells.values(), key=key)

    def _apply_slow(self, history: dict, events: list[dict]) -> None:
        self.events = events
        box = self.query_one("#throughput", VerticalScroll)
        # The bucket still filling is left out: it would always read as a drop.
        bucket_s = history.get("bucketMin", 10) * 60
        current = datetime.now(timezone.utc).timestamp() // bucket_s * bucket_s
        series_by = {
            m: [float(v) for t, v in sorted(s.items()) if datetime.fromisoformat(t).timestamp() < current] or [0.0]
            for m, s in history.get("series", {}).items()
        }
        width = max((len(v) for v in series_by.values()), default=1)
        for machine, values in sorted(series_by.items()):
            values = [0.0] * (width - len(values)) + values  # every series ends now: a shared time axis
            peak = int(max(values))
            label = f"{machine}  ·  last {values[-1]:.0f}  ·  peak {peak}  ·  over {dur(len(values) * history.get('bucketMin', 10) * 60)}"
            if machine in self.charts:
                caption, spark = self.charts[machine]
                caption.update(label)
                spark.data = values
            else:
                self.charts[machine] = (Static(label), Sparkline(values, summary_function=max))
                box.mount(*self.charts[machine])
        for machine in set(self.charts) - set(series_by):  # nothing from it in 24 h: its chart goes too
            for widget in self.charts.pop(machine):
                widget.remove()
        self._render_side()

    def _render_side(self) -> None:
        """The highlighted engine's recent events, or the whole feed (filtered by machine) when none is picked."""
        title = self.query_one("#side-title", Static)
        if self.selected:
            machine, engine = self.selected.rsplit(":", 1)
            shown = [ev for ev in self.events if ev["machine"] == machine and str(ev.get("engine")) == engine]
            title.update(Text.assemble(("Engine ", "bold"), f"{machine} #{engine}", ("  (esc: all events)", "grey50")))
        else:
            shown = [ev for ev in self.events if not self.machine_filter or ev["machine"] == self.machine_filter]
            title.update(Text.assemble(("Events ", "bold"), self.machine_filter or "all machines", ("  (m: filter)", "grey50")))
        lines = []
        for ev in shown[:60]:
            kind = ev["kind"]
            style = "yellow" if kind in ALERT_KINDS else "green" if kind in GOOD_KINDS else ""
            d = ev.get("detail") or {}
            extra = " · ".join(
                x for x in (
                    (ev.get("game_id") or "")[:8],
                    dur(d["seconds"]) if d.get("seconds") is not None else "",
                    f"{d['positions']} positions" if d.get("positions") is not None else "",
                    f"no progress for {dur(d['stuckS'])}" if d.get("stuckS") is not None else "",
                    f"silent for {dur(d['silentS'])}" if d.get("silentS") is not None else "",
                    f"{d['perHourNow']}/h, was {d.get('perHourBefore')}/h" if d.get("perHourNow") is not None else "",
                    CLEARED.get(d.get("cleared"), d.get("cleared") or ""),
                    str(d.get("error") or "")[:60],
                ) if x
            )
            who = ev["machine"] + (f" #{ev['engine']}" if ev.get("engine") is not None else "")
            lines.append(Text.assemble((clock(ev["at"]) + " ", "grey50"), (f"{who:<22}", "grey70"), (kind.replace("_", " "), style), f"  {extra}"))
        self.query_one("#side-body", Static).update(Text("\n").join(lines) if lines else Text("No events yet.", "grey50"))

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id == "engines" and event.row_key is not None and event.data_table.has_focus:
            self.selected = str(event.row_key.value)
            self._render_side()

    def on_descendant_focus(self, event) -> None:
        """Tabbing into the engines picks the row under the cursor (no highlight event fires for it)."""
        table = event.widget
        if getattr(table, "id", None) == "engines" and table.row_count:
            self.selected = str(table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value)
            self._render_side()

    def on_key(self, event) -> None:
        if event.key == "escape" and self.selected:
            self.selected = None
            self.query_one("#engines", DataTable).blur()
            self._render_side()

    def action_cycle_machine(self) -> None:
        names = [None] + sorted(m["machine"] for m in (self.snap or {}).get("machines", []))
        self.machine_filter = names[(names.index(self.machine_filter) + 1) % len(names)] if self.machine_filter in names else None
        self.selected = None
        self._render_side()

    def action_toggle_pause(self) -> None:
        self.paused = not self.paused
        self._render_kpis()

    def action_refresh(self) -> None:
        self.run_worker(self._fetch_snapshot, thread=True, exclusive=True, group="snap")
        self.run_worker(self._fetch_slow, thread=True, exclusive=True, group="slow")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--api", default=os.environ.get("SARCE_API", "http://127.0.0.1:8001"))
    parser.add_argument("--token", default=os.environ.get("SARCE_TOKEN"), help="Supabase access token (signed-in deployments)")
    args = parser.parse_args()
    MonitorApp(Api(args.api, args.token)).run()


if __name__ == "__main__":
    main()
