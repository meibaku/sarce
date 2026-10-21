"use client";

import { useEffect, useState } from "react";
import { HomeView, type HomeData } from "@/components/home/home-view";
import { EdgeState } from "@/components/ui/edge-state";
import { getHome, getSettings } from "@/lib/api";
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
    Promise.all([getHome(), getSettings().catch(() => null)])
      .then(([api, settings]) => {
        const data = toHomeData(api);
        const quiet = settings?.quietUntil
          ? new Date(`${settings.quietUntil}T00:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })
          : undefined;
        setState({ data: data && quiet ? { ...data, quietUntil: quiet } : data, status: "ready" });
      })
      .catch(() => setState({ data: null, status: "error" }));
  }, []);

  if (state.status === "loading") {
    // Never a full-screen spinner: a 2px progress line while Home loads.
    return <div className="h-[2px] w-1/3 animate-pulse bg-accent" role="progressbar" aria-label="Loading" />;
  }
  if (state.data) return <HomeView data={state.data} />;

  return state.status === "error" ? <EdgeState kind="offline" /> : <EdgeState kind="no-games" href="/onboarding" />;
}
