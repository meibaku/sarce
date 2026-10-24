"use client";

import { useEffect, useState } from "react";
import { HomeView, type HomeData } from "@/components/home/home-view";
import { EdgeState } from "@/components/ui/edge-state";
import { getHome, getSettings } from "@/lib/api";
import { gameMeta, timeAgo } from "@/lib/format";
import type { HomeApi } from "@/types/chess";

const LAST_VISIT = "sarce.lastVisit";

/** "Since your last visit: 6 games, 2 that felt like you, 1 real problem set." */
export function sessionLine(s: NonNullable<HomeApi["session"]>): string {
  const parts = [`${s.games} game${s.games === 1 ? "" : "s"} analysed`];
  if (s.feltLikeYou) parts.push(`${s.feltLikeYou} that felt like you`);
  if (s.realProblems) parts.push(`${s.realProblems} real problem${s.realProblems === 1 ? "" : "s"} set`);
  if (s.brilliant) parts.push(`${s.brilliant} with a Brilliant move`);
  return `Since your last visit: ${parts.join(", ")}.`;
}

function readLastVisit(): string | undefined {
  try {
    return localStorage.getItem(LAST_VISIT) ?? undefined;
  } catch {
    return undefined; // private window or blocked storage: no session line, nothing else changes
  }
}

function writeLastVisit() {
  try {
    localStorage.setItem(LAST_VISIT, new Date().toISOString());
  } catch {
    /* see readLastVisit */
  }
}

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
      range: brilliant.lo != null && brilliant.hi != null ? `likely ${brilliant.lo.toFixed(1)}–${brilliant.hi.toFixed(1)}%` : undefined,
      goalLo: brilliant.goalLo,
      goalHi: brilliant.goalHi,
      next: brilliant.nextLo != null && brilliant.nextHi != null ? { lo: brilliant.nextLo, hi: brilliant.nextHi } : null,
      gapLine: brilliant.gapLine ?? "",
      streak: stats?.streak == null ? null : `${stats.streak} game${stats.streak === 1 ? "" : "s"}`,
      soundRatio: stats?.soundRatio == null ? null : `${stats.soundRatio.toFixed(1)} : 1`,
      trapsSurvived: stats?.trapsSurvived == null ? null : `${Math.round(stats.trapsSurvived * 100)}%`,
    },
    session: api.session ? sessionLine(api.session) : undefined,
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
    Promise.all([getHome(undefined, readLastVisit()), getSettings().catch(() => null)])
      .then(([api, settings]) => {
        writeLastVisit();
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
