"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/shell/app-shell";
import { ChoiceButton } from "@/components/ui/buttons";
import { Card, SectionLabel } from "@/components/ui/card";
import { EdgeState } from "@/components/ui/edge-state";
import { timeAgo } from "@/lib/format";
import { listGames, type GameListItem } from "@/lib/api";

/*
 * All games, reached from Review. Newest first, or most chaotic first: the analysed games with the highest
 * chaos peak, which are usually the ones most worth reviewing. Counts use the style copy ("unsound chaos",
 * never "blunder").
 */

function detail(g: GameListItem, chaos: boolean) {
  if (chaos && g.chaosPeak != null) {
    return [
      `peak ${Math.round(g.chaosPeak * 100)}%`,
      g.realChaos ? `${g.realChaos} real chaos` : null,
      g.calculatedRisk ? `${g.calculatedRisk} calculated` : null,
      g.cheapChaos ? `${g.cheapChaos} unsound chaos` : null,
    ]
      .filter(Boolean)
      .join(" · ");
  }
  if (g.analysisStatus !== "complete") return g.analysisStatus === "failed" ? "analysis didn't finish" : "still being analysed";
  return g.brilliantPct != null ? `Brilliant ${g.brilliantPct.toFixed(1)}%` : "analysed";
}

export default function GamesPage() {
  const [chaos, setChaos] = useState(false);
  const [games, setGames] = useState<GameListItem[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setGames(null);
    listGames(chaos)
      .then((d) => setGames(d.games))
      .catch(() => setFailed(true));
  }, [chaos]);

  return (
    <AppShell title="review">
      <h1 className="text-[22px] font-medium">Your games</h1>
      <div className="flex gap-[6px]" role="radiogroup" aria-label="Order">
        <ChoiceButton chosen={!chaos} onClick={() => setChaos(false)} className="h-9 px-3">
          Newest
        </ChoiceButton>
        <ChoiceButton chosen={chaos} onClick={() => setChaos(true)} className="h-9 px-3">
          Most chaotic
        </ChoiceButton>
      </div>
      {failed ? (
        <EdgeState kind="offline" />
      ) : games === null ? (
        <div className="h-[2px] w-1/3 animate-pulse bg-accent" role="progressbar" aria-label="Loading" />
      ) : games.length === 0 ? (
        <EdgeState kind={chaos ? "analysing" : "no-games"} detail={chaos ? "Most chaotic fills in as games finish their chaos pass." : undefined} href="/onboarding" />
      ) : (
        <Card className="gap-0 !py-2">
          <SectionLabel className="py-2">{chaos ? "Highest chaos peak first" : "Newest first"}</SectionLabel>
          {games.map((g) => (
            <Link
              key={g.id}
              href={`/games/${g.id}/review`}
              className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-t border-hair py-[10px] hover:text-accent-text"
            >
              <span className="flex min-w-0 flex-col gap-[2px]">
                <span className="truncate text-[14px] font-medium">
                  vs {g.opponent ?? "an opponent"}
                  {g.opponentRating ? <span className="font-mono text-[12px] text-muted"> {g.opponentRating}</span> : null}
                </span>
                <span className="font-mono text-[11px] text-muted">{detail(g, chaos)}</span>
              </span>
              <span className="font-mono text-[11px] text-muted">
                {[g.timeControl, timeAgo(g.playedAt)].filter(Boolean).join(" · ")}
              </span>
            </Link>
          ))}
        </Card>
      )}
    </AppShell>
  );
}
