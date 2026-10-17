"use client";

import { useEffect, useState } from "react";
import { HomeView, type HomeData } from "@/components/home/home-view";
import { PrimaryLink } from "@/components/ui/buttons";
import { Card } from "@/components/ui/card";
import { getHome } from "@/lib/api";
import { gameMeta, timeAgo } from "@/lib/format";
import type { HomeApi } from "@/types/chess";

/** Maps GET /users/home onto the Home view. Null numbers stay null so the view dashes them. */
export function toHomeData(api: HomeApi): HomeData | null {
  const latest = api.latest;
  if (!latest) return null;
  const { brilliant, stats } = api;
  return {
    latest: {
      when: timeAgo(latest.playedAt),
      meta: gameMeta(latest),
      calibrated: latest.calibrated,
      styleRead: latest.styleRead,
      chaos: latest.chaos,
      highlight: latest.highlight,
      summaryHref: `/games/${latest.gameId}`,
      reviewHref: `/games/${latest.gameId}/review`,
      momentCount: latest.moments.length,
    },
    brilliant: {
      window: `last ${brilliant.games}`,
      value: brilliant.pct,
      spread: brilliant.spread,
      goalLo: brilliant.goalLo,
      goalHi: brilliant.goalHi,
      gapLine: brilliant.gapLine ?? "",
      streak: stats?.streak == null ? null : `${stats.streak} game${stats.streak === 1 ? "" : "s"}`,
      soundRatio: stats?.soundRatio == null ? null : `${stats.soundRatio.toFixed(1)} : 1`,
      trapsSurvived: stats?.trapsSurvived == null ? null : `${Math.round(stats.trapsSurvived * 100)}%`,
    },
    doors: [
      { kicker: "Weekly recap", title: `${brilliant.games} games analysed`, action: "Open the recap", href: "/recap" },
      { kicker: "Before your next game", title: "Today I want to: choose one", action: "Set it in Play", href: "/play" },
      { kicker: "Train", title: "Traps at your rating band", action: "Start a drill", href: "/train" },
    ],
  };
}

export function HomeScreen() {
  const [state, setState] = useState<{ data: HomeData | null; status: "loading" | "ready" | "error" }>({
    data: null,
    status: "loading",
  });

  useEffect(() => {
    getHome()
      .then((api) => setState({ data: toHomeData(api), status: "ready" }))
      .catch(() => setState({ data: null, status: "error" }));
  }, []);

  if (state.status === "loading") {
    // Never a full-screen spinner: a 2px progress line while Home loads.
    return <div className="h-[2px] w-1/3 animate-pulse bg-accent" role="progressbar" aria-label="Loading" />;
  }
  if (state.data) return <HomeView data={state.data} />;

  return (
    <Card className="items-start gap-3">
      <span className="text-[18px] font-medium">
        {state.status === "error" ? "Sarce can't reach its analysis service" : "No analysed games yet"}
      </span>
      <span className="text-[13px] leading-[1.55] text-ink-2">
        {state.status === "error"
          ? "Start the API, then reload. Your games and notes are safe."
          : "Import your recent games and Sarce will read the first one while you wait."}
      </span>
      <PrimaryLink href="/lab">{state.status === "error" ? "Open the lab" : "Import your games"}</PrimaryLink>
    </Card>
  );
}
