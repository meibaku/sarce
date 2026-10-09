"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  getActiveImportJob,
  getImportJobStatus,
  getStyleProfile,
  getTalBenchmark,
  getTimeline,
  getUserBaseline,
  listGames,
  listStyleMoments,
  startBackgroundImport,
} from "@/lib/api";
import { AnalysisWorkspace } from "./analysis-workspace";
import { BrilliantGauge } from "./brilliant-gauge";
import { BrilliantTimeline } from "./brilliant-timeline";
import { DistributionChart } from "./distribution-chart";
import { ImportGamesForm } from "./import-games-form";
import { ImportProgress } from "./import-progress";
import { StyleMoments } from "./style-moments";
import { StyleProfilePanel } from "./style-profile-panel";
import { StyleSummary } from "./style-summary";
import type {
  ImportJobStatus,
  ReferenceBenchmark,
  StyleMoment,
  StyleProfile,
  TimelinePoint,
  UserBaseline,
} from "@/types/chess";

const USERNAME_STORAGE_KEY = "sarce.chessComUsername";

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
  const [styleProfile, setStyleProfile] = useState<StyleProfile | null>(null);
  const [importJob, setImportJob] = useState<ImportJobStatus | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisRefreshToken, setAnalysisRefreshToken] = useState(0);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refreshData = useCallback(
    async (chessUsername?: string) => {
      const u = chessUsername ?? username ?? undefined;
      try {
        const [b, t, tal, profile] = await Promise.all([
          getUserBaseline(u),
          getTimeline(u),
          getTalBenchmark(),
          getStyleProfile(u).catch(() => null),
        ]);
        const momentRes = await listStyleMoments(u).catch(() => ({
          moments: [],
        }));
        setBaseline(b);
        setTimeline(t.points);
        setTalBenchmark(tal);
        setStyleProfile(profile);
        setMoments(momentRes.moments);
        return b;
      } catch {
        return null;
      }
    },
    [username],
  );

  const pollUntilAnalysisComplete = useCallback(
    async (chessUsername: string) => {
      setAnalyzing(true);
      for (let i = 0; i < 120; i++) {
        await new Promise((r) => setTimeout(r, 5000));
        const gamesRes = await listGames(chessUsername).catch(() => null);
        const pending = gamesRes?.games?.some(
          (g) =>
            g.analysisStatus === "pending" || g.analysisStatus === "processing",
        );
        await refreshData(chessUsername);
        setAnalysisRefreshToken((current) => current + 1);
        if (!pending) break;
      }
      setAnalyzing(false);
    },
    [refreshData],
  );

  const pollImportJob = useCallback(
    (jobId: string, chessUsername: string) => {
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current);
      }

      const tick = async () => {
        try {
          const status = await getImportJobStatus(jobId);
          setImportJob(status);
          await refreshData(chessUsername);
          setAnalysisRefreshToken((current) => current + 1);

          if (status.status === "queued" || status.status === "running") {
            pollTimerRef.current = setTimeout(tick, 2000);
            return;
          }

          if (status.status === "complete") {
            if (status.analyzeAfterImport && status.gamesNew > 0) {
              pollUntilAnalysisComplete(chessUsername);
            }
            return;
          }

          if (status.status === "failed") {
            setImportError(status.errorMessage ?? "Import failed.");
          }
        } catch (err) {
          setImportError(
            err instanceof Error ? err.message : "Import status check failed.",
          );
        } finally {
          setLoading(false);
        }
      };

      void tick();
    },
    [pollUntilAnalysisComplete, refreshData],
  );

  useEffect(() => {
    refreshData();
  }, [refreshData]);

  useEffect(() => {
    const savedUsername = sessionStorage.getItem(USERNAME_STORAGE_KEY);
    if (!savedUsername) return;

    setUsername(savedUsername);
    getActiveImportJob(savedUsername)
      .then(({ job }) => {
        if (!job) return;
        setImportJob(job);
        setLoading(job.status === "queued" || job.status === "running");
        pollImportJob(job.jobId, savedUsername);
      })
      .catch(() => null);
  }, [pollImportJob]);

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current);
      }
    };
  }, []);

  async function handleImport(chessUsername: string) {
    setLoading(true);
    setImportError(null);
    setImportJob(null);
    setUsername(chessUsername);
    sessionStorage.setItem(USERNAME_STORAGE_KEY, chessUsername);

    try {
      const job = await startBackgroundImport(chessUsername, true);
      setImportJob(job);
      pollImportJob(job.jobId, chessUsername);
    } catch (err) {
      setImportError(
        err instanceof Error
          ? err.message
          : "Import failed - is the API running on :8000?",
      );
      setLoading(false);
    }
  }

  const importBusy =
    loading ||
    analyzing ||
    importJob?.status === "queued" ||
    importJob?.status === "running";

  return (
    <div className="mx-auto max-w-6xl space-y-8 px-6 py-8">
      <section className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          <ImportGamesForm onImport={handleImport} loading={importBusy} />
          {importJob && (importBusy || importJob.status === "failed") && (
            <ImportProgress job={importJob} analyzing={analyzing} />
          )}
          {importError && (
            <p className="rounded-lg border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {importError}
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

      <StyleProfilePanel profile={styleProfile} />

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

      <AnalysisWorkspace
        username={username}
        baseline={baseline}
        talBenchmark={talBenchmark}
        refreshToken={analysisRefreshToken}
        onRefresh={async (chessUsername) => {
          await refreshData(chessUsername);
          setAnalysisRefreshToken((current) => current + 1);
        }}
      />
    </div>
  );
}
