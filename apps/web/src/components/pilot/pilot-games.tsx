"use client";

import { useEffect, useState } from "react";
import { PilotShell } from "@/components/pilot/pilot-shell";
import { PilotCard, PilotMessage } from "@/components/pilot/pilot-ui";
import { PilotGameRow } from "@/components/pilot/pilot-game-row";
import { listGames, type GameListItem } from "@/lib/api";

export function PilotGames() {
  const [games, setGames] = useState<GameListItem[] | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => { listGames(false, 50).then((result) => setGames(result.games)).catch(() => setFailed(true)); }, []);
  return (
    <PilotShell><main className="mx-auto max-w-[1120px] space-y-6 px-5 py-8">
      <div><p className="font-mono text-[11px] text-muted">Finished games · newest first</p><h1 className="pilot-serif mt-2 text-[32px]">Games</h1></div>
      {failed && <PilotMessage role="alert">Games could not be refreshed. Your saved reads are unchanged.</PilotMessage>}
      {games === null ? <div className="pilot-skeleton h-56 rounded-[8px]" /> : games.length === 0 ? <PilotCard className="p-6 text-ink-2">No finished games have been imported.</PilotCard> : <PilotCard className="divide-y divide-line overflow-hidden">{games.map((game) => <PilotGameRow key={game.id} game={game} />)}</PilotCard>}
    </main></PilotShell>
  );
}
