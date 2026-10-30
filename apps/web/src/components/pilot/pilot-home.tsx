"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { PilotShell } from "@/components/pilot/pilot-shell";
import { PilotButton, PilotCard, PilotMessage, PilotProgress } from "@/components/pilot/pilot-ui";
import { PilotGameRow } from "@/components/pilot/pilot-game-row";
import { usePilotStatus } from "@/components/pilot/pilot-status";
import { getHome, importChessComGames, importLichessGames, listGames, type GameListItem } from "@/lib/api";
import type { HomeApi } from "@/types/chess";

function dayLine(startsAt: string | null, endsAt: string | null) {
  if (!startsAt || !endsAt) return "Your style pilot";
  const now = Date.now();
  const start = new Date(startsAt).getTime();
  const end = new Date(endsAt).getTime();
  const total = Math.min(14, Math.max(1, Math.ceil((end - start) / 86_400_000)));
  const day = Math.min(total, Math.max(1, Math.floor((now - start) / 86_400_000) + 1));
  const left = Math.max(0, Math.ceil((end - now) / 86_400_000));
  return `Day ${day} of ${total} · ${left} ${left === 1 ? "day" : "days"} left`;
}

export function PilotHome() {
  const { status, refresh } = usePilotStatus();
  const [home, setHome] = useState<HomeApi | null>(null);
  const [games, setGames] = useState<GameListItem[]>([]);
  const [username, setUsername] = useState("");
  const [source, setSource] = useState<"chess_com" | "lichess">("chess_com");
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getHome(), listGames(false, 50)]).then(([nextHome, nextGames]) => {
      setHome(nextHome); setGames(nextGames.games);
    }).catch(() => setMessage("Sarce could not load the notebook. Your existing data is unchanged."))
      .finally(() => setLoading(false));
  }, []);
  if (!status) return null;
  if (loading) {
    return (
      <PilotShell>
        <main className="mx-auto max-w-[1120px] px-5 py-8" aria-label="Loading your style notebook">
          <div className="pilot-skeleton h-[520px] rounded-[8px]" />
        </main>
      </PilotShell>
    );
  }
  const ready = games.find((game) => game.analysisStatus === "complete" && !game.pilotResonance);
  const waiting = games.filter((game) => game.analysisStatus === "complete" && !game.pilotResonance).length;
  const oneIn = home?.brilliant.pct ? Math.max(1, Math.round(100 / home.brilliant.pct)) : null;
  const marker = Math.min(96, Math.max(4, ((home?.brilliant.pct ?? 0) / 1.5) * 100));

  async function importGames(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    try {
      const result = source === "chess_com" ? await importChessComGames(username, true) : await importLichessGames(username, true);
      setMessage(result.message); await refresh();
    } catch { setMessage("Import did not finish. Keep the username here and try again."); }
  }

  return (
    <PilotShell><main className="mx-auto max-w-[1120px] space-y-7 px-5 py-8">
      <div><p className="font-mono text-[12px] text-muted">{status.state === "active" ? dayLine(status.startsAt, status.endsAt) : `Pilot ${status.state}`}</p><h1 className="pilot-serif mt-2 text-[32px]">Your style notebook</h1></div>
      {message && <PilotMessage>{message}</PilotMessage>}
      <div className="grid gap-5 md:grid-cols-2">
        <PilotCard className="space-y-4 border-[1.5px] border-ink p-6"><h2 className="pilot-serif text-[24px]">{status.completedReads} of {status.targetReads} style reads completed</h2><PilotProgress completed={status.completedReads} waiting={waiting} /><p className="text-[13px] leading-6 text-ink-2">{waiting ? `${waiting} ${waiting === 1 ? "read is" : "reads are"} waiting for your answer. ` : ""}The pilot ends after your first 10 answered reads or two weeks, whichever comes first.</p>{ready ? <Link href={`/games/${ready.id}`} className="inline-flex min-h-11 items-center rounded-[6px] bg-ink px-5 font-medium text-surface">Open your latest style read</Link> : status.collectionActive ? <form onSubmit={importGames} className="grid gap-3 sm:grid-cols-[140px_1fr_auto]"><select value={source} onChange={(event) => setSource(event.target.value as typeof source)} className="min-h-11 rounded-[6px] border border-line-2 bg-surface px-2" aria-label="Game source"><option value="chess_com">Chess.com</option><option value="lichess">Lichess</option></select><input value={username} onChange={(event) => setUsername(event.target.value)} required placeholder="Your username" className="min-h-11 rounded-[6px] border border-line-2 bg-surface px-3" /><PilotButton>Import finished games</PilotButton></form> : <p className="font-medium">Collection is read-only.</p>}</PilotCard>
        <PilotCard className="space-y-4 p-6"><p className="font-mono text-[11px] font-medium uppercase tracking-[0.08em] text-muted">Brilliant · across your reads</p>{home?.brilliant.pct == null ? <><h2 className="pilot-serif text-[26px]">No Brilliant moves yet</h2><p className="text-[13px] leading-6 text-ink-2">That is a neutral observation, not a score. Each finished game adds evidence.</p></> : <><div className="flex flex-wrap items-baseline gap-x-3 gap-y-1"><strong className="font-mono text-[34px] font-normal text-[#9a4a0c]">{home.brilliant.pct.toFixed(1)}%</strong><span className="font-mono text-[12px] text-muted">{oneIn ? `about 1 in ${oneIn} moves` : `across ${home.brilliant.games} games`}</span></div><div className="relative pt-7"><span className="absolute top-0 -translate-x-1/2 whitespace-nowrap rounded-full border border-ink bg-ink px-2 py-1 font-mono text-[9px] text-surface" style={{ left: `${marker}%` }}>Your reads</span><div className="relative h-3 rounded-full border-[1.5px] border-ink bg-surface"><span className="absolute inset-y-[-1.5px] left-[13.33%] w-[26.67%] border-[1.5px] border-[#b4570f] bg-[#f6e7d6]" /><span className="absolute inset-y-[-6px] w-0.5 bg-ink" style={{ left: `${marker}%` }} /></div><div className="relative mt-2 h-4 font-mono text-[10px] text-muted"><span className="absolute left-0">0</span><span className="absolute left-[13.33%] -translate-x-1/2">0.2</span><span className="absolute left-[40%] -translate-x-1/2">0.6</span><span className="absolute right-0">1.5%</span></div></div><div className="grid grid-cols-3 gap-2 text-center text-[10px] leading-4 text-muted"><span>More solid<br />0–0.2%</span><strong className="font-medium text-[#9a4a0c]">Tal reference<br />0.2–0.6%</strong><span>Above reference<br />0.6–1.5%</span></div><p className="text-[13px] leading-6 text-ink-2">A reference range, not a target or score. With {home.brilliant.games} reads, one Brilliant move changes this a lot; it settles as reads add up.</p></>}</PilotCard>
      </div>
      <section><div className="mb-3 flex items-center justify-between"><h2 className="text-[16px] font-medium">Recent games</h2><Link href="/games" className="min-h-11 content-center text-accent-text underline underline-offset-4">All games</Link></div><PilotCard className="divide-y divide-line overflow-hidden">{games.length ? games.slice(0, 4).map((game) => <PilotGameRow key={game.id} game={game} />) : <p className="p-5 text-ink-2">No finished games imported yet.</p>}</PilotCard></section>
    </main></PilotShell>
  );
}
