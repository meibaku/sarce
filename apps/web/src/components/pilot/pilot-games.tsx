"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PilotShell } from "@/components/pilot/pilot-shell";
import { PilotCard, PilotMessage } from "@/components/pilot/pilot-ui";
import { listGames, type GameListItem } from "@/lib/api";

function status(game: GameListItem) {
  if (game.pilotResonance) return `Answered · ${game.pilotResonance}`;
  if (game.analysisStatus === "complete") return "Ready";
  if (game.analysisStatus === "failed") return "Couldn’t finish";
  if (game.analysisStatus === "processing") return game.analysisProgress == null ? "Being read" : `Being read · ${Math.round(game.analysisProgress)}%`;
  return "Waiting";
}

function metadata(game: GameListItem) {
  const result = game.result === "win" ? "Won" : game.result === "loss" ? "Lost" : game.result === "draw" ? "Draw" : null;
  const side = game.userColor ? game.userColor[0].toUpperCase() + game.userColor.slice(1) : null;
  return [result, game.playedAt ? new Date(game.playedAt).toLocaleDateString() : null, game.timeControl, side, game.totalMoves ? `${game.totalMoves} moves` : null].filter(Boolean).join(" · ");
}

export function PilotGames() {
  const [games, setGames] = useState<GameListItem[] | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => { listGames(false, 50).then((result) => setGames(result.games)).catch(() => setFailed(true)); }, []);
  return (
    <PilotShell><main className="mx-auto max-w-[1120px] space-y-6 px-5 py-8">
      <div><p className="font-mono text-[11px] text-muted">Finished games · newest first</p><h1 className="pilot-serif mt-2 text-[32px]">Games</h1></div>
      {failed && <PilotMessage role="alert">Games could not be refreshed. Your saved reads are unchanged.</PilotMessage>}
      {games === null ? <div className="pilot-skeleton h-56 rounded-[8px]" /> : games.length === 0 ? <PilotCard className="p-6 text-ink-2">No finished games have been imported.</PilotCard> : <PilotCard className="divide-y divide-line">{games.map((game) => <article key={game.id} className="grid gap-3 p-4 sm:grid-cols-[1fr_auto] sm:items-center"><div><h2 className="font-medium">vs {game.opponent ?? "an opponent"}</h2><p className="mt-1 font-mono text-[11px] text-muted">{metadata(game)}</p><p className="mt-1 text-[13px] text-ink-2">{game.analysisStatus === "failed" ? "The analysis did not finish. Your imported game is still safe." : game.analysisStatus === "complete" ? (game.pilotResonance ? "Your saved style read is available." : "Your post-game style read is ready for your answer.") : "Sarce is preparing this finished game."}</p></div><div className="flex flex-col items-end gap-2"><span className="rounded-full bg-panel px-3 py-1 font-mono text-[11px]">{status(game)}</span>{game.analysisStatus === "complete" && <Link href={`/games/${game.id}`} className="min-h-11 content-center text-accent-text underline">{game.pilotResonance ? "Open read" : "Open read and answer"}</Link>}{game.analysisStatus === "failed" && game.externalUrl && <a href={game.externalUrl} target="_blank" rel="noreferrer" className="min-h-11 content-center text-accent-text underline">Open in {game.externalUrl.includes("lichess") ? "Lichess" : "Chess.com"} ↗</a>}</div></article>)}</PilotCard>}
    </main></PilotShell>
  );
}
