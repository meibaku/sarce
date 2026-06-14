"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getTalBenchmark,
  getTimeline,
  getUserBaseline,
  importChessComGames,
  listStyleMoments,
} from "@/lib/api";
import { BrilliantGauge } from "./brilliant-gauge";
import { BrilliantTimeline } from "./brilliant-timeline";
import { DistributionChart } from "./distribution-chart";
import { ImportGamesForm } from "./import-games-form";
import { StyleMoments } from "./style-moments";
import { StyleSummary } from "./style-summary";
import type {
  ReferenceBenchmark,
  StyleMoment,
  TimelinePoint,
  UserBaseline,
} from "@/types/chess";

const EMPTY_BASELINE: UserBaseline = {
  brilliantPct: 0,
  distribution: {
    best: 0,
    excellent: 0,
    good: 0,
    inaccuracy: 0,
    mistake: 0,
    blunder: 0,
    miss: 0,
    brilliant: 0,
  },
  gamesAnalyzed: 0,
  targetBrilliantMin: 6,
  targetBrilliantMax: 10,
};

export function Dashboard() {
  const [baseline, setBaseline] = useState<UserBaseline>(EMPTY_BASELINE);
  const [talBenchmark, setTalBenchmark] = useState<ReferenceBenchmark | null>(
    null,
  );
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);
  const [moments, setMoments] = useState<StyleMoment[]>([]);
  const [importStatus, setImportStatus] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const refreshData = useCallback(
    async (chessUsername?: string) => {
      const u = chessUsername ?? username ?? undefined;
      try {
        const [b, t, tal] = await Promise.all([
          getUserBaseline(u),
          getTimeline(u),
          getTalBenchmark(),
        ]);
        const momentRes = await listStyleMoments(u).catch(() => ({
          moments: [],
        }));
        setBaseline(b);
        setTimeline(t.points);
        setTalBenchmark(tal);
        setMoments(momentRes.moments);
        return b;
      } catch {
        return null;
      }
    },
    [username],
  );

  useEffect(() => {
    refreshData();
  }, [refreshData]);

  async function handleImport(chessUsername: string) {
    setLoading(true);
    setImportStatus(null);
    setUsername(chessUsername);
    try {
      const result = await importChessComGames(chessUsername);
      setImportStatus(result.message);
      if (result.imported > 0) {
        await refreshData(chessUsername);
      }
    } catch (err) {
      setImportStatus(
        err instanceof Error
          ? err.message
          : "Import failed - is the API running on :8000?",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8 px-6 py-8">
      <section className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          <ImportGamesForm onImport={handleImport} loading={loading} />
          {importStatus && (
            <p className="rounded-lg border border-white/10 bg-surface px-4 py-3 text-sm text-foreground/80">
              {importStatus}
            </p>
          )}
          <StyleSummary baseline={baseline} />
        </div>
        <BrilliantGauge
          brilliantPct={baseline.brilliantPct}
          targetMin={baseline.targetBrilliantMin}
          targetMax={baseline.targetBrilliantMax}
        />
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <DistributionChart
          title="Your move quality"
          distribution={baseline.distribution}
          gamesAnalyzed={baseline.gamesAnalyzed}
        />
        <DistributionChart
          title={`${talBenchmark?.playerName ?? "Mikhail Tal"} reference`}
          distribution={talBenchmark?.distribution ?? EMPTY_BASELINE.distribution}
          gamesAnalyzed={talBenchmark?.gamesSampled ?? 0}
          subtitle={
            talBenchmark?.status === "complete"
              ? "Calibrated from Tal PGN corpus"
              : "Run: python -m scripts.process_tal_benchmark"
          }
        />
      </section>

      <section className="rounded-xl border border-white/10 bg-surface p-6">
        <h2 className="mb-2 text-lg font-medium">Brilliant % over time</h2>
        <p className="mb-4 text-sm text-foreground/50">
          Target band: {baseline.targetBrilliantMin}-{baseline.targetBrilliantMax}%
        </p>
        <BrilliantTimeline
          points={timeline}
          targetMin={baseline.targetBrilliantMin}
          targetMax={baseline.targetBrilliantMax}
        />
      </section>

      <StyleMoments moments={moments} />
    </div>
  );
}
