"use client";

import { useEffect, useState } from "react";
import { createScoutingReport, deleteScoutingReport, listScoutingReports } from "@/lib/api";
import type { ScoutingReport } from "@/types/chess";

const MOTIF_LABELS: Record<string, string> = {
  sacrifice: "Sacrifices",
  fork: "Forks",
  pin: "Pins",
  skewer: "Skewers",
  discovered_attack: "Discovered attacks",
  hanging_piece: "Pieces left loose",
};

export function ScoutingPanel() {
  const [reports, setReports] = useState<ScoutingReport[]>([]);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    listScoutingReports()
      .then((res) => setReports(res.reports))
      .catch(() => setReports([]));
  }, []);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const username = (data.get("username") as string).trim();
    if (!username) return;
    setBusy(true);
    setStatus(null);
    try {
      const report = await createScoutingReport(username, data.get("source") as "chess_com" | "lichess");
      setReports((current) => [report, ...current.filter((r) => r.id !== report.id)]);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Could not build the report");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id: string) {
    await deleteScoutingReport(id).catch(() => null);
    setReports((current) => current.filter((r) => r.id !== id));
  }

  return (
    <section className="rounded-xl border border-white/10 bg-surface p-6">
      <h2 className="text-lg font-medium">Opponent prep</h2>
      <p className="mt-1 text-sm text-foreground/50">
        A private summary of a player&apos;s recent finished games. Only you can see it, their
        games are not stored, and you can delete it at any time.
      </p>

      <form className="mt-4 flex flex-wrap gap-3" onSubmit={handleSubmit}>
        <select
          name="source"
          aria-label="Site"
          defaultValue="chess_com"
          disabled={busy}
          className="rounded-lg border border-white/10 bg-background px-3 py-2 text-sm"
        >
          <option value="chess_com">Chess.com</option>
          <option value="lichess">Lichess</option>
        </select>
        <input
          name="username"
          type="text"
          placeholder="Opponent username"
          disabled={busy}
          className="min-w-40 flex-1 rounded-lg border border-white/10 bg-background px-4 py-2 text-sm outline-none focus:border-accent/50"
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded-lg border border-accent/40 px-4 py-2 text-sm font-medium text-accent transition hover:border-accent disabled:opacity-50"
        >
          {busy ? "Preparing..." : "Prepare"}
        </button>
      </form>
      {status && <p className="mt-3 text-sm text-foreground/60">{status}</p>}

      <div className="mt-4 space-y-3">
        {reports.map((entry) => {
          const { report } = entry;
          const motifs = Object.entries(report.motifsPer100Moves)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 3);
          return (
            <div key={entry.id} className="rounded-md border border-white/10 bg-background/40 p-4 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium">
                  {entry.username}{" "}
                  <span className="font-mono text-xs text-foreground/45">
                    {entry.source === "lichess" ? "Lichess" : "Chess.com"} · {entry.gamesSampled} games
                  </span>
                </p>
                <button
                  type="button"
                  onClick={() => handleDelete(entry.id)}
                  className="rounded border border-white/15 px-2 py-0.5 text-xs text-foreground/60 transition hover:border-white/30"
                >
                  Delete
                </button>
              </div>
              <div className="mt-3 grid gap-3 sm:grid-cols-3">
                <List title="As White" items={report.openingsAsWhite.map((o) => `${o.name} (${o.games})`)} />
                <List title="As Black" items={report.openingsAsBlack.map((o) => `${o.name} (${o.games})`)} />
                <List
                  title="Rough tendencies per 100 moves"
                  items={[
                    ...motifs.map(([tag, rate]) => `${MOTIF_LABELS[tag] ?? tag}: ${rate}`),
                    `Gambits per game: ${report.ideasPerGame.gambit ?? 0}`,
                  ]}
                />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function List({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="mb-1 text-xs text-foreground/45">{title}</p>
      {items.length === 0 ? (
        <p className="text-foreground/40">-</p>
      ) : (
        <ul className="space-y-0.5 text-foreground/75">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
