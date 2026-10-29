"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { PilotShell } from "@/components/pilot/pilot-shell";
import { PilotButton, PilotCard, PilotMessage, PilotProgress } from "@/components/pilot/pilot-ui";
import { usePilotStatus } from "@/components/pilot/pilot-status";
import { getHome, importChessComGames, importLichessGames, listGames, type GameListItem } from "@/lib/api";
import type { HomeApi } from "@/types/chess";

function chip(game: GameListItem) {
  if (game.pilotResonance) return `Answered · ${game.pilotResonance}`;
  if (game.analysisStatus === "complete") return "Waiting for you";
  if (game.analysisStatus === "failed") return "Couldn’t finish";
  return game.analysisStatus === "processing" ? "Being read" : "Waiting";
}

export function PilotHome() {
  const { status, refresh } = usePilotStatus();
  const [home, setHome] = useState<HomeApi | null>(null);
  const [games, setGames] = useState<GameListItem[]>([]);
  const [username, setUsername] = useState("");
  const [source, setSource] = useState<"chess_com" | "lichess">("chess_com");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getHome(), listGames(false, 5)]).then(([nextHome, nextGames]) => {
      setHome(nextHome); setGames(nextGames.games);
    }).catch(() => setMessage("Sarce could not load the notebook. Your existing data is unchanged."));
  }, []);
  if (!status) return null;
  const ready = games.find((game) => game.analysisStatus === "complete" && !game.pilotResonance);

  async function importGames(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    try {
      const result = source === "chess_com" ? await importChessComGames(username, true) : await importLichessGames(username, true);
      setMessage(result.message); await refresh();
    } catch { setMessage("Import did not finish. Keep the username here and try again."); }
  }

  return (
    <PilotShell><main className="mx-auto max-w-[1080px] space-y-7 px-5 py-8">
      <div><p className="font-mono text-[11px] text-muted">{status.state === "active" ? "Your 14-day style pilot" : `Pilot ${status.state}`}</p><h1 className="pilot-serif mt-2 text-[32px]">Your style notebook</h1></div>
      {message && <PilotMessage>{message}</PilotMessage>}
      <div className="grid gap-5 md:grid-cols-2">
        <PilotCard className="space-y-4 border-ink p-6"><h2 className="pilot-serif text-[24px]">{status.completedReads} of {status.targetReads} style reads completed</h2><PilotProgress completed={status.completedReads} /><p className="text-[13px] leading-6 text-ink-2">The pilot ends after your first 10 answered reads or two weeks, whichever comes first.</p>{ready ? <Link href={`/games/${ready.id}`} className="inline-flex min-h-11 items-center rounded-[7px] bg-ink px-5 font-medium text-surface">Open your latest style read</Link> : status.collectionActive ? <form onSubmit={importGames} className="grid gap-3 sm:grid-cols-[140px_1fr_auto]"><select value={source} onChange={(event) => setSource(event.target.value as typeof source)} className="min-h-11 rounded-[6px] border border-line-2 bg-surface px-2" aria-label="Game source"><option value="chess_com">Chess.com</option><option value="lichess">Lichess</option></select><input value={username} onChange={(event) => setUsername(event.target.value)} required placeholder="Your username" className="min-h-11 rounded-[6px] border border-line-2 bg-surface px-3" /><PilotButton>Import finished games</PilotButton></form> : <p className="font-medium">Collection is read-only.</p>}</PilotCard>
        <PilotCard className="space-y-4 p-6"><p className="font-mono text-[11px] uppercase text-muted">Brilliant · across your reads</p>{home?.brilliant.pct == null ? <><h2 className="pilot-serif text-[26px]">No Brilliant moves yet</h2><p className="text-[13px] leading-6 text-ink-2">That is a neutral observation, not a score. Each finished game adds evidence.</p></> : <><div className="flex items-baseline gap-3"><strong className="font-mono text-[31px] font-normal">{home.brilliant.pct.toFixed(1)}%</strong><span className="font-mono text-[11px] text-muted">across {home.brilliant.games} games</span></div><div className="h-2 rounded-full border border-line-2"><div className="h-full bg-accent-tint" style={{ marginLeft: "13.3%", width: "26.7%" }} /></div><p className="text-[13px] leading-6 text-ink-2">The evidence-backed Tal-style reference band is 0.2–0.6%. With a small sample, each move changes the figure a lot.</p></>}</PilotCard>
      </div>
      <section><div className="mb-3 flex items-center justify-between"><h2 className="text-[16px] font-medium">Recent games</h2><Link href="/games" className="min-h-11 content-center text-accent-text underline">All games</Link></div><PilotCard className="divide-y divide-line">{games.length ? games.slice(0, 4).map((game) => <Link key={game.id} href={game.analysisStatus === "complete" ? `/games/${game.id}` : "/games"} className="flex min-h-16 items-center justify-between gap-4 px-4 py-3"><span><strong className="block text-[14px]">vs {game.opponent ?? "an opponent"}</strong><span className="font-mono text-[11px] text-muted">{game.timeControl ?? "finished game"}</span></span><span className="rounded-full bg-panel px-3 py-1 font-mono text-[11px]">{chip(game)}</span></Link>) : <p className="p-5 text-ink-2">No finished games imported yet.</p>}</PilotCard></section>
    </main></PilotShell>
  );
}
