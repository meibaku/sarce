"use client";

import { useEffect, useMemo, useState } from "react";
import { getMonitorEvents, getMonitorHistory, getMonitorSnapshot, monitorStreamUrl } from "@/lib/api";
import type { MonitorEngine, MonitorEvent, MonitorHistory, MonitorMachine, MonitorSnapshot } from "@/types/chess";

/*
 * Analysis monitor (dev mode): every machine and engine at work, per game, with resources, throughput and drops.
 * The live snapshot arrives as server-sent events (/monitor/stream) and updates in place, with no flicker; when the
 * stream can't open (sign-in required, a proxy), it falls back to polling every 3 s. History and events refresh each
 * minute and on every new snapshot that changed the event count.
 */

const SERIES = ["var(--color-accent)", "var(--color-sound)", "var(--color-checkin)", "var(--color-ink-2)", "var(--color-fp-5)"];
const KIND: Record<string, string> = {
  claimed: "claimed",
  node_game_done: "searched",
  game_done: "analysed",
  finished_from_node: "finished from node",
  game_failed: "failed",
  node_started: "node started",
  offline: "offline",
  stalled: "stalled",
  rate_drop: "rate drop",
  recovered: "recovered",
  updated: "updated",
};
const WARN = new Set(["game_failed", "offline", "stalled", "rate_drop"]);

function dur(s: number | null | undefined) {
  if (s == null) return "–";
  if (s < 60) return `${Math.round(s)}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m ${String(Math.round(s % 60)).padStart(2, "0")}s`;
  const h = s / 3600;
  return h < 48 ? `${h.toFixed(1)} h` : `${(h / 24).toFixed(1)} days`;
}

function n(v: number | null | undefined) {
  return v == null ? "–" : v.toLocaleString();
}

function clock(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function hhmm(t: number) {
  return new Date(t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

const CLEARED: Record<string, string> = { offline: "back online", stalled: "progressing again", drop: "speed back" };

/** The useful part of an event's detail: game, timings, positions, and what an alert or recovery was about. */
function eventDetail(ev: MonitorEvent) {
  const d = (ev.detail ?? {}) as Record<string, unknown>;
  const num = (k: string) => (typeof d[k] === "number" ? (d[k] as number) : null);
  const parts = [
    ev.game_id ? ev.game_id.slice(0, 8) : null,
    num("seconds") != null ? dur(num("seconds")) : null,
    num("positions") != null ? `${num("positions")} positions` : null,
    num("stuckS") != null ? `no progress for ${dur(num("stuckS"))}` : null,
    num("silentS") != null ? `silent for ${dur(num("silentS"))}` : null,
    num("perHourNow") != null ? `${num("perHourNow")}/h, was ${num("perHourBefore")}/h` : null,
    typeof d.cleared === "string" ? CLEARED[d.cleared] ?? d.cleared : null,
    typeof d.bundle === "string" ? `bundle ${d.bundle.slice(0, 8)}` : null,
    typeof d.error === "string" ? d.error : null,
  ];
  return parts.filter(Boolean).join(" · ");
}

function Meter({ value, width = "w-full", tone = "bg-accent" }: { value: number | null; width?: string; tone?: string }) {
  const pct = value == null ? 0 : Math.max(0, Math.min(100, value));
  return (
    <span className={`relative inline-block h-[6px] overflow-hidden rounded-[3px] bg-hair ${width}`} aria-hidden>
      <span className={`absolute inset-y-0 left-0 ${tone} transition-[width] duration-500`} style={{ width: `${pct}%` }} />
    </span>
  );
}

function Kpi({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="flex min-w-[130px] flex-1 flex-col gap-[2px] rounded-[8px] border border-line bg-surface px-4 py-3">
      <span className="font-mono text-[10px] uppercase tracking-[0.06em] text-muted">{label}</span>
      <span className="font-mono text-[20px] font-medium tabular-nums">{value}</span>
      {sub && <span className="text-[11px] text-muted">{sub}</span>}
    </div>
  );
}

function EngineRow({ e, events, open, onToggle }: { e: MonitorEngine; events: MonitorEvent[]; open: boolean; onToggle: () => void }) {
  const frac = e.total ? e.done / e.total : 0;
  const busy = e.state !== "idle" && !e.stale;
  const g = e.game;
  const vs = g ? `vs ${g.opponent ?? "?"}${g.opponent_rating ? ` (${g.opponent_rating})` : ""} · ${g.user_color ?? "?"} · ${g.time_control ?? "?"}` : null;
  return (
    <>
      <tr className="cursor-pointer border-t border-hair align-middle hover:bg-panel" onClick={onToggle}>
        <td className="py-2 pl-3 font-mono text-[12px] text-muted">
          <button
            type="button"
            aria-expanded={open}
            aria-label={`Engine ${e.engine}: recent events`}
            onClick={(ev) => { ev.stopPropagation(); onToggle(); }}
            className="rounded-[3px] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            <span className="mr-1 inline-block w-3 text-faint">{open ? "▾" : "▸"}</span>
            {e.engine}
          </button>
        </td>
        <td className="py-2 text-[12px]">
          <span className={`inline-block rounded-[4px] px-[6px] py-[1px] font-mono text-[11px] ${busy ? "bg-accent-tint text-accent-text" : "bg-hair text-muted"}`}>
            {e.stale ? "silent" : e.state}
          </span>
        </td>
        <td className="max-w-[260px] truncate py-2 text-[12px]" title={vs ?? undefined}>
          {vs ?? <span className="text-faint">–</span>}
        </td>
        <td className="py-2 pr-2">
          <div className="flex items-center gap-2">
            <Meter value={frac * 100} width="w-[110px]" />
            <span className="font-mono text-[11px] tabular-nums text-muted">{e.total ? `${e.done}/${e.total}` : "–"}</span>
          </div>
        </td>
        <td className="py-2 font-mono text-[11px] tabular-nums">{busy ? dur(e.elapsedS) : "–"}</td>
        <td className="py-2 font-mono text-[11px] tabular-nums text-muted">{busy ? dur(e.etaS) : "–"}</td>
        <td className="py-2 font-mono text-[11px] tabular-nums">{e.cpu == null ? "–" : `${e.cpu.toFixed(0)}%`}</td>
        <td className="py-2 font-mono text-[11px] tabular-nums">{e.rss_mb == null ? "–" : `${e.rss_mb.toFixed(0)} MB`}</td>
        <td className="py-2 pr-3 text-right font-mono text-[11px] tabular-nums text-muted">
          {n(e.games_today)} · {dur(e.last_game_s)}
        </td>
      </tr>
      {open && (
        <tr className="bg-page">
          <td colSpan={9} className="px-4 py-2">
            <div className="flex flex-col gap-1 text-[12px]">
              {e.game_id && <span className="font-mono text-[11px] text-muted">game {e.game_id}{g?.played_at ? ` · played ${new Date(g.played_at).toLocaleString()}` : ""}</span>}
              {events.length === 0 && <span className="text-muted">No events for this engine yet.</span>}
              {events.slice(0, 12).map((ev) => (
                <span key={ev.id} className={WARN.has(ev.kind) ? "text-checkin" : "text-ink-2"}>
                  <span className="font-mono text-[11px] text-muted">{clock(ev.at)}</span> {KIND[ev.kind] ?? ev.kind}
                  {eventDetail(ev) ? ` · ${eventDetail(ev)}` : ""}
                </span>
              ))}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function MachineCard({ m, events, openEngines, toggle }: { m: MonitorMachine; events: MonitorEvent[]; openEngines: Set<string>; toggle: (k: string) => void }) {
  const [open, setOpen] = useState(true);
  return (
    <section className="overflow-hidden rounded-[8px] border border-line bg-surface">
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="flex w-full flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3 text-left hover:bg-panel">
        <span className="flex items-center gap-2">
          <span className={`inline-block size-[9px] rounded-full ${m.online ? "bg-sound" : "bg-checkin"}`} aria-label={m.online ? "online" : "offline"} />
          <span className="text-[15px] font-medium">{m.machine}</span>
          <span className="rounded-[4px] bg-hair px-[6px] py-[1px] font-mono text-[10px] uppercase text-muted">{m.role}</span>
        </span>
        <span className="flex items-center gap-2 font-mono text-[11px] text-muted">
          CPU <Meter value={m.cpu} width="w-[70px]" /> <span className="tabular-nums text-ink">{m.cpu == null ? "–" : `${m.cpu.toFixed(0)}%`}</span>
        </span>
        <span className="flex items-center gap-2 font-mono text-[11px] text-muted">
          RAM <Meter value={m.mem_used == null ? null : m.mem_used * 100} width="w-[70px]" tone="bg-ink-2" />
          <span className="tabular-nums text-ink">{m.mem_used == null ? "–" : `${Math.round(m.mem_used * 100)}% of ${m.mem_total_gb} GB`}</span>
        </span>
        <span className="font-mono text-[11px] text-muted">
          {n(m.rate?.perHourNow)} games/h now · {n(m.rate?.lastHour)} last hour
        </span>
        <span className="ml-auto font-mono text-[11px] text-muted">
          {m.online ? `up ${dur(m.uptime_s)}` : `silent ${dur(m.silentS)}`}
          {m.bundle ? ` · ${m.bundle.slice(0, 8)}` : ""} · {open ? "▾" : "▸"}
        </span>
      </button>
      {open && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] border-collapse">
            <thead>
              <tr className="font-mono text-[10px] uppercase tracking-[0.05em] text-muted">
                {["engine", "state", "game", "positions", "elapsed", "eta", "cpu", "memory", "today · last"].map((h, i) => (
                  <th key={h} className={`py-[6px] font-normal ${i === 0 ? "pl-3 text-left" : i === 8 ? "pr-3 text-right" : "text-left"}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {m.engineRows.map((e) => {
                const key = `${m.machine}:${e.engine}`;
                return (
                  <EngineRow
                    key={key}
                    e={e}
                    events={events.filter((ev) => ev.machine === m.machine && ev.engine === e.engine)}
                    open={openEngines.has(key)}
                    onToggle={() => toggle(key)}
                  />
                );
              })}
              {m.engineRows.length === 0 && (
                <tr className="border-t border-hair">
                  <td colSpan={9} className="px-4 py-3 text-[12px] text-muted">No engine has reported yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

/**
 * Games per hour per machine and in total. The axis spans the data actually there (at most 24 h), not a fixed day:
 * a monitor started an hour ago would otherwise be a spike against the right edge. The current bucket is left out
 * until it's complete, or it would always look like a drop.
 */
function Throughput({ history }: { history: MonitorHistory }) {
  const W = 900, H = 180, L = 36, R = 14, T = 12, B = 24;
  const bucketMs = history.bucketMin * 60_000;
  const perHour = 60 / history.bucketMin;
  const current = Math.floor(new Date(history.to).getTime() / bucketMs) * bucketMs;
  const machines = Object.keys(history.series).sort();
  const lines = machines.map((m) =>
    Object.entries(history.series[m])
      .map(([t, v]) => [new Date(t).getTime(), v * perHour] as [number, number])
      .filter(([t]) => t < current)
      .sort((a, b) => a[0] - b[0]),
  );
  const totals = new Map<number, number>();
  lines.flat().forEach(([t, v]) => totals.set(t, (totals.get(t) ?? 0) + v));
  const total = [...totals.entries()].sort((a, b) => a[0] - b[0]);
  const caption = (
    <figcaption className="flex flex-wrap items-baseline gap-4">
      <span className="font-mono text-[10px] uppercase tracking-[0.06em] text-muted">
        Games per hour{total.length ? ` · since ${hhmm(total[0][0])}` : ""}
      </span>
      {total.length > 0 && (
        <span className="flex items-center gap-1 text-[11px]">
          <span className="inline-block h-[3px] w-4 rounded bg-ink" />
          all machines
        </span>
      )}
      {machines.map((m, i) => (
        <span key={m} className="flex items-center gap-1 text-[11px]">
          <span className="inline-block h-[3px] w-4 rounded" style={{ background: SERIES[i % SERIES.length] }} />
          {m}
        </span>
      ))}
      <span className="ml-auto text-[11px] text-muted">{history.bucketMin}-minute buckets · dashed: restarts, drops, stalls, offline</span>
    </figcaption>
  );
  if (total.length === 0) {
    return (
      <figure className="flex flex-col gap-2 rounded-[8px] border border-line bg-surface px-4 py-3">
        {caption}
        <p className="py-6 text-[12px] text-muted">The first point appears once a full {history.bucketMin} minutes of work is in.</p>
      </figure>
    );
  }
  const start = total[0][0];
  // To now: the gap after the last point is the bucket still filling, and recent marks land where they happened.
  const end = Math.max(new Date(history.to).getTime(), start + bucketMs);
  const peak = Math.max(1, ...total.map(([, v]) => v));
  const step = [5, 10, 20, 25, 50, 100, 200, 500].find((st) => peak / st <= 4) ?? 1000;
  const top = Math.ceil(peak / step) * step;
  const x = (t: number) => L + ((t - start) / (end - start)) * (W - L - R);
  const y = (v: number) => T + (1 - v / top) * (H - T - B);
  const tickMs = [10, 30, 60, 120, 180, 360].map((m) => m * 60_000).find((ms) => (end - start) / ms <= 6) ?? 720 * 60_000;
  const ticks: number[] = [];
  for (let t = Math.ceil(start / tickMs) * tickMs; t <= end; t += tickMs) ticks.push(t);
  const pts = (series: [number, number][]) => series.map(([t, v]) => `${x(t).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  return (
    <figure className="flex flex-col gap-2 rounded-[8px] border border-line bg-surface px-4 py-3">
      {caption}
      <svg viewBox={`0 0 ${W} ${H}`} className="h-[180px] w-full" role="img" aria-label="Games per hour, per machine and in total">
        {Array.from({ length: top / step + 1 }, (_, i) => i * step).map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke={v === 0 ? "var(--color-line)" : "var(--color-hair)"} />
            <text x={L - 6} y={y(v) + 3} fontSize="10" textAnchor="end" fill="var(--color-muted)">{v}</text>
          </g>
        ))}
        {ticks.map((t) => (
          <text key={t} x={x(t)} y={H - 6} fontSize="10" textAnchor="middle" fill="var(--color-muted)">{hhmm(t)}</text>
        ))}
        {history.marks
          .filter((mk) => new Date(mk.at).getTime() >= start)
          .map((mk, i) => {
            const at = x(new Date(mk.at).getTime());
            return (
              <line key={i} x1={at} x2={at} y1={T} y2={y(0)} stroke={WARN.has(mk.kind) ? "var(--color-checkin)" : "var(--color-line-3)"} strokeDasharray="2 3">
                <title>{`${clock(mk.at)} · ${KIND[mk.kind] ?? mk.kind}${mk.machine ? ` · ${mk.machine}` : ""}`}</title>
              </line>
            );
          })}
        {lines.map((series, i) =>
          series.length === 1 ? (
            // A single point draws no line: a dot, so a machine that just started still shows.
            <circle key={machines[i]} cx={x(series[0][0])} cy={y(series[0][1])} r="2.5" fill={SERIES[i % SERIES.length]} />
          ) : (
            <polyline key={machines[i]} points={pts(series)} fill="none" stroke={SERIES[i % SERIES.length]} strokeWidth="1.5" strokeLinejoin="round" />
          ),
        )}
        <polyline points={pts(total)} fill="none" stroke="var(--color-ink)" strokeWidth="2.25" strokeLinejoin="round" />
        {total.map(([t, v]) => (
          <circle key={t} cx={x(t)} cy={y(v)} r="3" fill="var(--color-ink)">
            <title>{`${hhmm(t)}–${hhmm(t + bucketMs)} · ${Math.round(v)} games/h`}</title>
          </circle>
        ))}
      </svg>
    </figure>
  );
}

export function MonitorView() {
  const [snap, setSnap] = useState<MonitorSnapshot | null>(null);
  const [history, setHistory] = useState<MonitorHistory | null>(null);
  const [events, setEvents] = useState<MonitorEvent[]>([]);
  const [live, setLive] = useState<"stream" | "polling" | "connecting" | "stale">("connecting");
  const [filter, setFilter] = useState("");
  const [openEngines, setOpenEngines] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  // Live snapshot: the stream, or polling when it can't open.
  useEffect(() => {
    let poll: ReturnType<typeof setInterval> | null = null;
    const startPolling = () => {
      if (poll) return;
      setLive("polling");
      const tick = () => getMonitorSnapshot().then((s) => { setSnap(s); setError(null); }).catch(() => setError("The API isn't answering."));
      tick();
      poll = setInterval(tick, 3000);
    };
    getMonitorSnapshot().then(setSnap).catch(() => setError("The API isn't answering."));
    let source: EventSource | null = null;
    // A stream that opens but never delivers (a buffering proxy) falls back to polling too.
    const silent = setTimeout(() => { source?.close(); startPolling(); }, 10_000);
    try {
      source = new EventSource(monitorStreamUrl());
      source.addEventListener("snapshot", (ev) => {
        clearTimeout(silent);
        setSnap(JSON.parse((ev as MessageEvent).data));
        setLive("stream");
        setError(null);
      });
      // The API is up but its database reads fail: say so instead of showing the last snapshot as live.
      source.addEventListener("problem", () => {
        clearTimeout(silent);
        setLive("stale");
        setError("The database isn't answering; showing the last snapshot.");
      });
      source.onerror = () => {
        clearTimeout(silent);
        source?.close();
        startPolling();
      };
    } catch {
      clearTimeout(silent);
      startPolling();
    }
    return () => {
      clearTimeout(silent);
      source?.close();
      if (poll) clearInterval(poll);
    };
  }, []);

  // History and events: each minute, and when the snapshot changes.
  const snapKey = snap ? `${snap.queue.complete}:${snap.alerts.length}:${snap.machines.map((m) => m.engineRows.map((e) => e.game_id).join()).join()}` : "";
  useEffect(() => {
    const load = () => {
      getMonitorHistory(24, 10).then(setHistory).catch(() => undefined);
      getMonitorEvents(150).then((r) => setEvents(r.events)).catch(() => undefined);
    };
    load();
    const t = setInterval(load, 60_000);
    return () => clearInterval(t);
  }, [snapKey]);

  const shownEvents = useMemo(() => (filter ? events.filter((e) => e.machine === filter) : events), [events, filter]);
  const toggle = (k: string) => setOpenEngines((s) => { const next = new Set(s); if (next.has(k)) next.delete(k); else next.add(k); return next; });

  if (!snap) return <p className="text-[13px] text-muted">{error ?? "Connecting to the analysis monitor…"}</p>;
  const q = snap.queue;
  const frac = q.total ? q.complete / q.total : 0;
  const engines = snap.machines.reduce((a, m) => a + m.engineRows.filter((e) => e.state !== "idle" && !e.stale).length, 0);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-baseline gap-3">
        <h1 className="text-[22px] font-medium">Analysis monitor</h1>
        <span className="font-mono text-[11px] text-muted">
          {live === "stream" ? "live" : live === "polling" ? "polling every 3 s" : live === "stale" ? "stale" : "connecting"} · updated {clock(snap.at)}
        </span>
        {error && <span className="font-mono text-[11px] text-checkin">{error}</span>}
      </div>

      {snap.alerts.length > 0 && (
        <div className="flex flex-col gap-1 rounded-[8px] border-[1.5px] border-checkin bg-surface px-4 py-3" role="status">
          {snap.alerts.map((a) => (
            <span key={a.key} className="text-[13px]">
              <span className="font-medium text-checkin">{KIND[a.kind] ?? a.kind}</span> · {a.machine}
              {a.kind === "rate_drop" ? ` · ${a.perHourNow}/h now, ${a.perHourBefore}/h before` : ""}
              {a.kind === "stalled" ? ` · engine ${a.engine}, no progress for ${dur(a.stuckS as number)}` : ""}
              {a.kind === "offline" ? ` · silent for ${dur(a.silentS as number)}` : ""}
            </span>
          ))}
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        <div className="flex min-w-[260px] flex-[2] flex-col gap-2 rounded-[8px] border border-line bg-surface px-4 py-3">
          <span className="font-mono text-[10px] uppercase tracking-[0.06em] text-muted">Queue</span>
          <span className="font-mono text-[20px] font-medium tabular-nums">
            {n(q.complete)} <span className="text-[13px] text-muted">of {n(q.total)} · {(frac * 100).toFixed(1)}%</span>
          </span>
          <Meter value={frac * 100} />
        </div>
        <Kpi label="Left" value={n(q.pending)} sub={`${n(q.processing)} analysing · ${n(q.failed)} failed`} />
        <Kpi label="Speed" value={`${n(snap.perHour)}/h`} sub="games finished, last hour" />
        <Kpi label="Time to go" value={dur(snap.etaHours == null ? null : snap.etaHours * 3600)} sub="at the last hour's pace" />
        <Kpi label="Machines" value={`${snap.machines.filter((m) => m.online).length}/${snap.machines.length}`} sub={`${engines} engines busy`} />
      </div>

      {snap.machines.map((m) => (
        <MachineCard key={m.machine} m={m} events={events} openEngines={openEngines} toggle={toggle} />
      ))}

      {history && <Throughput history={history} />}

      <section className="flex flex-col rounded-[8px] border border-line bg-surface">
        <div className="flex flex-wrap items-center gap-3 border-b border-hair px-4 py-2">
          <span className="font-mono text-[10px] uppercase tracking-[0.06em] text-muted">Events</span>
          <select value={filter} onChange={(e) => setFilter(e.target.value)} className="ml-auto rounded-[6px] border border-line-2 bg-surface px-2 py-1 text-[12px]" aria-label="Filter events by machine">
            <option value="">all machines</option>
            {snap.machines.map((m) => (
              <option key={m.machine} value={m.machine}>{m.machine}</option>
            ))}
          </select>
        </div>
        <ol className="max-h-[320px] overflow-y-auto">
          {shownEvents.map((ev) => (
            <li key={ev.id} className="grid grid-cols-[80px_150px_minmax(0,1fr)] gap-3 border-t border-hair px-4 py-[6px] text-[12px] first:border-t-0">
              <span className="font-mono text-[11px] text-muted">{clock(ev.at)}</span>
              <span className="truncate font-mono text-[11px] text-muted">{ev.machine ?? "–"}{ev.engine != null ? ` #${ev.engine}` : ""}</span>
              <span className={WARN.has(ev.kind) ? "text-checkin" : ""}>
                {KIND[ev.kind] ?? ev.kind}
                {eventDetail(ev) ? ` · ${eventDetail(ev)}` : ""}
              </span>
            </li>
          ))}
          {shownEvents.length === 0 && <li className="px-4 py-3 text-[12px] text-muted">No events yet.</li>}
        </ol>
      </section>
    </div>
  );
}
