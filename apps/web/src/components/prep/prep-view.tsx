"use client";

import { useEffect, useState } from "react";
import { PrimaryButton, TextButton } from "@/components/ui/buttons";
import { AutoGrid, Card, SectionLabel } from "@/components/ui/card";
import { createScoutingReport, deleteScoutingReport, listScoutingReports } from "@/lib/api";
import type { ScoutingReport } from "@/types/chess";

/*
 * Opponent prep (CHAOS_PLAN M8 scouting, moved here from the retired /lab dashboard). A private
 * summary of a player's recent finished games: only usernames you type, finished games only, their
 * games are not stored, and every report can be deleted. Reached from Play.
 */

const MOTIFS: Record<string, string> = {
  sacrifice: "Sacrifices",
  fork: "Forks",
  pin: "Pins",
  skewer: "Skewers",
  discovered_attack: "Discovered attacks",
  hanging_piece: "Pieces left loose",
};

const field = "h-10 rounded-[6px] border-[1.5px] border-line-2 bg-surface px-3 text-[13px]";

function List({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="font-mono text-[10px] text-muted">{title}</span>
      {items.length === 0 ? (
        <span className="text-[13px] text-faint">Not enough games</span>
      ) : (
        items.map((item) => (
          <span key={item} className="text-[13px] leading-[1.45] text-ink-2">
            {item}
          </span>
        ))
      )}
    </div>
  );
}

export function PrepView() {
  const [reports, setReports] = useState<ScoutingReport[] | null>(null);
  const [username, setUsername] = useState("");
  const [source, setSource] = useState<"chess_com" | "lichess">("chess_com");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    listScoutingReports()
      .then((r) => setReports(r.reports))
      .catch(() => setReports([]));
  }, []);

  async function build() {
    const name = username.trim();
    if (!name || busy) return;
    setBusy(true);
    setStatus(null);
    try {
      const report = await createScoutingReport(name, source);
      setReports((current) => [report, ...(current ?? []).filter((r) => r.id !== report.id)]);
      setUsername("");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "The report couldn't be built. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="flex flex-wrap items-baseline gap-3">
        <h1 className="text-[22px] font-medium">Opponent prep</h1>
        <span className="font-mono text-[11px] text-muted">finished games only · private · delete any time</span>
      </div>

      <Card lead className="gap-3 !p-[18px]">
        <SectionLabel className="!text-accent-text">Who are you playing?</SectionLabel>
        <span className="text-[13px] leading-[1.5] text-ink-2">
          A summary of their recent finished games: openings, time controls and rough tendencies. Only you see it, their
          games aren&apos;t kept, and it is never shown to anyone.
        </span>
        <form
          className="flex flex-wrap gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            build();
          }}
        >
          <select value={source} onChange={(e) => setSource(e.target.value as typeof source)} aria-label="Site" className={field} disabled={busy}>
            <option value="chess_com">Chess.com</option>
            <option value="lichess">Lichess</option>
          </select>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Their username"
            aria-label="Opponent username"
            autoComplete="off"
            disabled={busy}
            className={`${field} min-w-[180px] flex-1 placeholder:text-faint`}
          />
          <PrimaryButton type="submit" disabled={busy || !username.trim()} className="!px-5">
            {busy ? "Reading their games…" : "Build report"}
          </PrimaryButton>
        </form>
        {status && <span className="text-[12px] text-muted">{status}</span>}
      </Card>

      {reports && reports.length === 0 && <span className="text-[13px] text-muted">No reports yet.</span>}
      <div className="flex flex-col gap-3">
        {reports?.map((entry) => {
          const { report } = entry;
          const motifs = Object.entries(report.motifsPer100Moves)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 3);
          const results = ["win", "draw", "loss"].map((k) => `${report.results[k] ?? 0} ${k === "win" ? "won" : k === "draw" ? "drawn" : "lost"}`);
          return (
            <Card key={entry.id} className="gap-3 !px-5 !py-[18px]">
              <div className="flex flex-wrap items-baseline gap-3">
                <span className="text-[16px] font-medium">{entry.username}</span>
                <span className="font-mono text-[11px] text-muted">
                  {entry.source === "lichess" ? "Lichess" : "Chess.com"} · {entry.gamesSampled} finished games · {results.join(" · ")}
                </span>
                <TextButton
                  className="ml-auto !text-muted"
                  onClick={() => {
                    deleteScoutingReport(entry.id).catch(() => null);
                    setReports((current) => (current ?? []).filter((r) => r.id !== entry.id));
                  }}
                >
                  Delete
                </TextButton>
              </div>
              <AutoGrid min={200}>
                <List title="AS WHITE" items={report.openingsAsWhite.slice(0, 3).map((o) => `${o.name} (${o.games})`)} />
                <List title="AS BLACK" items={report.openingsAsBlack.slice(0, 3).map((o) => `${o.name} (${o.games})`)} />
                <List
                  title="ROUGH TENDENCIES · PER 100 MOVES"
                  items={[...motifs.map(([tag, rate]) => `${MOTIFS[tag] ?? tag}: ${rate}`), `Gambits per game: ${report.ideasPerGame.gambit ?? 0}`]}
                />
                <List title="TIME CONTROLS" items={report.timeControls.slice(0, 3).map((t) => `${t.name} (${t.games})`)} />
              </AutoGrid>
            </Card>
          );
        })}
      </div>
    </>
  );
}
