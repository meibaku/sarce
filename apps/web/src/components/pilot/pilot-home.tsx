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

function gameMeta(game: GameListItem) {
  const result = game.result === "win" ? "Won" : game.result === "loss" ? "Lost" : game.result === "draw" ? "Draw" : null;
  const side = game.userColor ? game.userColor[0].toUpperCase() + game.userColor.slice(1) : null;
  return [result, game.playedAt ? new Date(game.playedAt).toLocaleDateString() : null, game.timeControl, side, game.totalMoves ? `${game.totalMoves} moves` : null].filter(Boolean).join(" · ");
}

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

  useEffect(() => {
    Promise.all([getHome(), listGames(false, 50)]).then(([nextHome, nextGames]) => {
      setHome(nextHome); setGames(nextGames.games);
    }).catch(() => setMessage("Sarce could not load the notebook. Your existing data is unchanged."));
  }, []);
  if (!status) return null;
  const ready = games.find((game) => game.analysisStatus === "complete" && !game.pilotResonance);
  const waiting = games.filter((game) => game.analysisStatus === "complete" && !game.pilotResonance).length;
  const oneIn = home?.brilliant.pct ? Math.max(1, Math.round(100 / home.brilliant.pct)) : null;
  const marker = Math.min(100, ((home?.brilliant.pct ?? 0) / 1.5) * 100);

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
        <PilotCard className="space-y-4 p-6"><p className="font-mono text-[11px] font-medium uppercase tracking-[0.08em] text-muted">Brilliant · across your reads</p>{home?.brilliant.pct == null ? <><h2 className="pilot-serif text-[26px]">No Brilliant moves yet</h2><p className="text-[13px] leading-6 text-ink-2">That is a neutral observation, not a score. Each finished game adds evidence.</p></> : <><div className="flex items-baseline gap-3"><strong className="font-mono text-[34px] font-normal text-[#9a4a0c]">{home.brilliant.pct.toFixed(1)}%</strong><span className="font-mono text-[12px] text-muted">{oneIn ? `1 in ${oneIn} moves` : `across ${home.brilliant.games} games`}</span></div><div className="relative my-1 h-[10px] rounded-full border-[1.5px] border-ink bg-surface"><span className="absolute inset-y-[-1.5px] left-[13.33%] w-[26.67%] border-[1.5px] border-[#b4570f] bg-[#f6e7d6]" /><span className="absolute inset-y-[-7px] w-0.5 bg-ink" style={{ left: `${marker}%` }} /></div><div className="flex justify-between font-mono text-[11px] text-muted"><span>0</span><span>band 0.2–0.6%</span><span>1.5%</span></div><p className="text-[13px] leading-6 text-ink-2">Sarce&apos;s reference band is 0.2–0.6%. With {home.brilliant.games} reads, one Brilliant move changes this a lot. It settles as reads add up.</p></>}</PilotCard>
      </div>
      <section><div className="mb-3 flex items-center justify-between"><h2 className="text-[16px] font-medium">Recent games</h2><Link href="/games" className="min-h-11 content-center text-accent-text underline">All games</Link></div><PilotCard className="divide-y divide-line">{games.length ? games.slice(0, 4).map((game) => <Link key={game.id} href={game.analysisStatus === "complete" ? `/games/${game.id}` : "/games"} className="grid min-h-16 grid-cols-[minmax(0,1fr)_auto] items-center gap-4 px-4 py-3"><span><strong className="block text-[14px]">vs {game.opponent ?? "an opponent"}</strong><span className="font-mono text-[11px] text-muted">{gameMeta(game)}</span><span className="mt-1 block text-[13px] text-ink-2">{game.analysisStatus === "complete" ? (game.pilotResonance ? "Your saved style read." : "Your style read is ready for your answer.") : game.analysisStatus === "failed" ? "The finished game is safe; its read did not finish." : "Sarce is preparing this finished game."}</span></span><span className="rounded-full bg-panel px-3 py-1 font-mono text-[11px]">{chip(game)}</span></Link>) : <p className="p-5 text-ink-2">No finished games imported yet.</p>}</PilotCard></section>
    </main></PilotShell>
  );
}
