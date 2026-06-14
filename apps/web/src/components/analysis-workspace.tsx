"use client";

import { useEffect, useMemo, useState } from "react";
import {
  analyzePendingGames,
  getGameDetail,
  listGames,
} from "@/lib/api";
import { ChessReplay } from "./chess-replay";
import type {
  AnalyzedMove,
  GameDetail,
  GameSummary,
  MoveSignal,
  MoveQuality,
  ReferenceBenchmark,
  UserBaseline,
} from "@/types/chess";

const QUALITY_LABELS: Record<MoveQuality, string> = {
  brilliant: "Brilliant",
  best: "Best",
  excellent: "Excellent",
  good: "Good",
  inaccuracy: "Inaccuracy",
  mistake: "Mistake",
  miss: "Miss",
  blunder: "Blunder",
};

const QUALITY_STYLES: Record<MoveQuality, string> = {
  brilliant: "border-brilliant/50 bg-brilliant/15 text-brilliant",
  best: "border-emerald-400/40 bg-emerald-400/10 text-emerald-200",
  excellent: "border-sky-400/40 bg-sky-400/10 text-sky-200",
  good: "border-white/15 bg-white/5 text-foreground/80",
  inaccuracy: "border-yellow-400/40 bg-yellow-400/10 text-yellow-100",
  mistake: "border-orange-400/40 bg-orange-400/10 text-orange-100",
  miss: "border-pink-400/40 bg-pink-400/10 text-pink-100",
  blunder: "border-red-400/40 bg-red-400/10 text-red-100",
};

const REVIEW_QUALITIES = new Set<MoveQuality>([
  "brilliant",
  "miss",
  "blunder",
  "mistake",
  "inaccuracy",
]);

const SIGNAL_LABELS: Record<MoveSignal, string> = {
  forced: "Forced",
  top_engine_choice: "Engine pick",
  top_three_choice: "Top 3",
  clearly_best: "Clearly best",
  sacrifice: "Sacrifice",
  exchange_sacrifice: "Exchange sac",
  brilliant_sacrifice: "Sound sac",
  evaluation_swing: "Eval swing",
  tactical_resource: "Tactical",
  momentum_shift: "Momentum",
  breakthrough_sacrifice: "Breakthrough",
  missed_tactic: "Missed tactic",
  critical_error: "Critical",
  clean_move: "Clean",
};

const SIGNAL_STYLES: Partial<Record<MoveSignal, string>> = {
  brilliant_sacrifice: "border-brilliant/50 bg-brilliant/15 text-brilliant",
  sacrifice: "border-brilliant/35 bg-brilliant/10 text-brilliant",
  exchange_sacrifice: "border-violet-300/40 bg-violet-400/10 text-violet-100",
  breakthrough_sacrifice: "border-fuchsia-300/40 bg-fuchsia-400/10 text-fuchsia-100",
  tactical_resource: "border-cyan-300/40 bg-cyan-400/10 text-cyan-100",
  momentum_shift: "border-emerald-300/40 bg-emerald-400/10 text-emerald-100",
  evaluation_swing: "border-amber-300/40 bg-amber-400/10 text-amber-100",
  missed_tactic: "border-pink-300/40 bg-pink-400/10 text-pink-100",
  critical_error: "border-red-300/40 bg-red-400/10 text-red-100",
};

type IntentState = "saw" | "calculated" | "stumbled";

interface AnalysisWorkspaceProps {
  username: string | null;
  baseline: UserBaseline;
  talBenchmark: ReferenceBenchmark | null;
  refreshToken: number;
  onRefresh?: (username?: string) => Promise<unknown>;
}

function moveLabel(move: AnalyzedMove) {
  const number = Math.floor(move.ply / 2) + 1;
  return move.ply % 2 === 0 ? `${number}.` : `${number}...`;
}

function fmtPct(value: number | null | undefined) {
  return value == null ? "-" : `${value.toFixed(1)}%`;
}

function fmtEval(value: number | null) {
  if (value == null) return "-";
  return value > 0 ? `+${value.toFixed(2)}` : value.toFixed(2);
}

function evalSwing(move: AnalyzedMove) {
  if (move.evalBefore == null || move.evalAfter == null) return null;
  return move.evalAfter - move.evalBefore;
}

function styleFitLabel(baseline: UserBaseline) {
  if (baseline.gamesAnalyzed === 0) return "No baseline";
  if (baseline.brilliantPct < baseline.targetBrilliantMin) return "Under target";
  if (baseline.brilliantPct > baseline.targetBrilliantMax) return "Overheated";
  return "In band";
}

function moveSignal(move: AnalyzedMove) {
  if (move.highlight) return move.highlight;
  if (move.signals.includes("brilliant_sacrifice")) return "Sound sacrifice";
  if (move.signals.includes("breakthrough_sacrifice")) return "Breakthrough";
  if (move.signals.includes("exchange_sacrifice")) return "Exchange sacrifice";
  if (move.signals.includes("momentum_shift")) return "Momentum shift";
  if (move.signals.includes("tactical_resource")) return "Tactical resource";
  if (move.signals.includes("forced")) return "Forced";
  const swing = evalSwing(move);
  if (move.quality === "brilliant") return "Sound sacrifice";
  if (move.quality === "miss") return "Tide missed";
  if (move.quality === "blunder") return "Tide lost";
  if ((move.cpLoss ?? 0) >= 80) return "Review";
  if (swing != null && swing >= 0.5) return "Pressure gained";
  if (move.quality === "best" || move.quality === "excellent") return "Clean";
  return "Stable";
}

function criticalMoves(game: GameDetail | null) {
  if (!game) return [];
  return game.moves.filter(
    (move) =>
      REVIEW_QUALITIES.has(move.quality) ||
      (move.cpLoss ?? 0) >= 80 ||
      move.signals.some((signal) =>
        [
          "sacrifice",
          "exchange_sacrifice",
          "breakthrough_sacrifice",
          "tactical_resource",
          "momentum_shift",
          "evaluation_swing",
        ].includes(signal),
      ),
  );
}

export function AnalysisWorkspace({
  username,
  baseline,
  talBenchmark,
  refreshToken,
  onRefresh,
}: AnalysisWorkspaceProps) {
  const [games, setGames] = useState<GameSummary[]>([]);
  const [selectedGameId, setSelectedGameId] = useState<string | null>(null);
  const [selectedGame, setSelectedGame] = useState<GameDetail | null>(null);
  const [selectedPly, setSelectedPly] = useState<number | null>(null);
  const [replayIndex, setReplayIndex] = useState(-1);
  const [intentNotes, setIntentNotes] = useState<Record<string, string>>({});
  const [intentState, setIntentState] = useState<Record<string, IntentState>>({});
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadGames() {
      const res = await listGames(username ?? undefined).catch(() => ({
        games: [],
      }));
      if (cancelled) return;
      setGames(res.games);
      setSelectedGameId((current) => current ?? res.games[0]?.id ?? null);
    }
    loadGames();
    return () => {
      cancelled = true;
    };
  }, [username, refreshToken]);

  useEffect(() => {
    let cancelled = false;
    async function loadDetail() {
      if (!selectedGameId) {
        setSelectedGame(null);
        return;
      }
      const detail = await getGameDetail(
        selectedGameId,
        username ?? undefined,
      ).catch(() => null);
      if (cancelled) return;
      setSelectedGame(detail);
      setSelectedPly((current) => {
        if (current != null && detail?.moves.some((m) => m.ply === current)) {
          return current;
        }
        return criticalMoves(detail)[0]?.ply ?? detail?.moves[0]?.ply ?? null;
      });
    }
    loadDetail();
    return () => {
      cancelled = true;
    };
  }, [selectedGameId, username, refreshToken]);

  const selectedMove = useMemo(
    () => selectedGame?.moves.find((move) => move.ply === selectedPly) ?? null,
    [selectedGame, selectedPly],
  );

  useEffect(() => {
    if (!selectedGame || selectedPly == null) {
      setReplayIndex(-1);
      return;
    }
    const index = selectedGame.mainline.findIndex((move) => move.ply === selectedPly);
    setReplayIndex(index >= 0 ? index : -1);
  }, [selectedGame, selectedPly]);

  const reviewMoves = useMemo(() => criticalMoves(selectedGame), [selectedGame]);
  const noteKey =
    selectedGame && selectedMove
      ? `${selectedGame.id}:${selectedMove.ply}`
      : null;
  const currentIntent = noteKey ? intentState[noteKey] ?? "calculated" : "calculated";
  const notesForMove = noteKey ? intentNotes[noteKey] ?? "" : "";
  const talDelta =
    talBenchmark?.status === "complete"
      ? baseline.brilliantPct - talBenchmark.brilliantPct
      : null;
  const targetGap =
    baseline.brilliantPct < baseline.targetBrilliantMin
      ? baseline.targetBrilliantMin - baseline.brilliantPct
      : baseline.brilliantPct > baseline.targetBrilliantMax
        ? baseline.brilliantPct - baseline.targetBrilliantMax
        : 0;
  const totalClassified = selectedGame?.totalMoves ?? selectedGame?.moves.length ?? 0;
  const distribution = selectedGame?.distribution;
  const forcingMoves = distribution
    ? (distribution.brilliant ?? 0) +
      (distribution.miss ?? 0) +
      (distribution.blunder ?? 0) +
      (distribution.mistake ?? 0)
    : 0;
  const forcingPct = totalClassified
    ? (forcingMoves / totalClassified) * 100
    : 0;
  const signalCounts = useMemo(() => {
    const counts: Partial<Record<MoveSignal, number>> = {};
    for (const move of selectedGame?.moves ?? []) {
      for (const signal of move.signals) {
        counts[signal] = (counts[signal] ?? 0) + 1;
      }
    }
    return counts;
  }, [selectedGame]);
  const topSignals = Object.entries(signalCounts)
    .sort(([, a], [, b]) => (b ?? 0) - (a ?? 0))
    .slice(0, 4) as [MoveSignal, number][];

  async function runAnalysis() {
    setBusy(true);
    setStatus(null);
    try {
      const res = await analyzePendingGames(username ?? undefined);
      setStatus(res.message);
      await onRefresh?.(username ?? undefined);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Analysis request failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-foreground/45">
            Move analysis
          </p>
          <h2 className="mt-1 text-2xl font-semibold">Style lab</h2>
        </div>
        <button
          type="button"
          onClick={runAnalysis}
          disabled={busy}
          className="h-10 rounded-md border border-accent/40 px-4 text-sm font-medium text-accent transition hover:border-accent disabled:opacity-50"
        >
          {busy ? "Analyzing..." : "Analyze pending"}
        </button>
      </div>

      {status && (
        <div className="rounded-md border border-white/10 bg-surface px-4 py-3 text-sm text-foreground/70">
          {status}
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-4">
        <Metric label="Style fit" value={styleFitLabel(baseline)} />
        <Metric label="Target gap" value={targetGap === 0 ? "0.0%" : `${targetGap.toFixed(1)}%`} />
        <Metric label="Tal delta" value={talDelta == null ? "-" : `${talDelta >= 0 ? "+" : ""}${talDelta.toFixed(1)}%`} />
        <Metric label="Forcing share" value={`${forcingPct.toFixed(1)}%`} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[320px_1fr]">
        <div className="rounded-lg border border-white/10 bg-surface p-3">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-medium text-foreground/80">Games</h3>
            <span className="text-xs text-foreground/45">{games.length}</span>
          </div>
          <div className="space-y-2">
            {games.slice(0, 12).map((game) => (
              <button
                key={game.id}
                type="button"
                onClick={() => setSelectedGameId(game.id)}
                className={`w-full rounded-md border px-3 py-2 text-left transition ${
                  selectedGameId === game.id
                    ? "border-accent/60 bg-accent/10"
                    : "border-white/10 bg-background/40 hover:border-white/25"
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="truncate text-sm font-medium">
                    {game.opponent ?? "Unknown"}
                  </span>
                  <span className="text-xs uppercase text-foreground/45">
                    {game.result}
                  </span>
                </div>
                <div className="mt-1 flex items-center justify-between gap-3 text-xs text-foreground/50">
                  <span>{game.analysisStatus}</span>
                  <span>{fmtPct(game.brilliantPct)}</span>
                </div>
              </button>
            ))}
            {games.length === 0 && (
              <div className="rounded-md border border-white/10 bg-background/40 px-3 py-6 text-sm text-foreground/50">
                No imported games
              </div>
            )}
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
          <div className="rounded-lg border border-white/10 bg-surface p-4">
            <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h3 className="text-lg font-semibold">
                  {selectedGame ? `vs ${selectedGame.opponent}` : "No game selected"}
                </h3>
                <p className="text-sm text-foreground/50">
                  {selectedGame?.playedAt
                    ? new Date(selectedGame.playedAt).toLocaleString()
                    : "Awaiting game data"}
                </p>
              </div>
              <div className="flex gap-2 text-xs">
                <Badge label={selectedGame?.analysisStatus ?? "idle"} />
                <Badge label={selectedGame?.userColor ?? "-"} />
              </div>
            </div>

            <div className="mb-4 grid gap-2 sm:grid-cols-3">
              <Metric label="Brilliant" value={fmtPct(selectedGame?.brilliantPct)} compact />
              <Metric label="Moves" value={`${totalClassified || "-"}`} compact />
              <Metric label="Review queue" value={`${reviewMoves.length}`} compact />
            </div>

            {topSignals.length > 0 && (
              <div className="mb-4 flex flex-wrap gap-2">
                {topSignals.map(([signal, count]) => (
                  <SignalBadge key={signal} signal={signal} suffix={`${count}`} />
                ))}
              </div>
            )}

            <div className="grid gap-2">
              {(selectedGame?.moves ?? []).map((move) => (
                <button
                  key={move.ply}
                  type="button"
                  onClick={() => setSelectedPly(move.ply)}
                  className={`grid grid-cols-[44px_minmax(56px,76px)_minmax(0,1fr)_64px] items-center gap-2 rounded-md border px-3 py-2 text-left text-sm transition sm:grid-cols-[52px_84px_minmax(0,1fr)_72px] ${
                    selectedPly === move.ply
                      ? "border-accent/60 bg-accent/10"
                      : "border-white/10 bg-background/35 hover:border-white/25"
                  }`}
                >
                  <span className="font-mono text-xs text-foreground/45">
                    {moveLabel(move)}
                  </span>
                  <span className="truncate font-mono">{move.san ?? move.uci}</span>
                  <span className="flex min-w-0 flex-wrap gap-1">
                    <span
                      className={`w-fit rounded border px-2 py-1 text-xs ${QUALITY_STYLES[move.quality]}`}
                    >
                      {QUALITY_LABELS[move.quality]}
                    </span>
                    {move.signals.slice(0, 2).map((signal) => (
                      <SignalBadge key={signal} signal={signal} />
                    ))}
                  </span>
                  <span className="text-right font-mono text-xs text-foreground/55">
                    {move.cpLoss == null ? "-" : `${move.cpLoss.toFixed(0)} cp`}
                  </span>
                </button>
              ))}
              {selectedGame && selectedGame.moves.length === 0 && (
                <div className="rounded-md border border-white/10 bg-background/40 px-4 py-8 text-sm text-foreground/50">
                  {selectedGame.analysisStatus}
                </div>
              )}
            </div>
          </div>

          <aside className="space-y-4">
            <ChessReplay
              initialFen={selectedGame?.initialFen ?? ""}
              mainline={selectedGame?.mainline ?? []}
              replayIndex={replayIndex}
              onReplayIndexChange={setReplayIndex}
              userColor={selectedGame?.userColor ?? null}
            />

            <div className="rounded-lg border border-white/10 bg-surface p-4">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-medium text-foreground/80">
                  Engine reality
                </h3>
                {selectedMove && <Badge label={moveSignal(selectedMove)} />}
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Metric label="Before" value={fmtEval(selectedMove?.evalBefore ?? null)} compact />
                <Metric label="After" value={fmtEval(selectedMove?.evalAfter ?? null)} compact />
                <Metric
                  label="Swing"
                  value={selectedMove ? fmtEval(evalSwing(selectedMove)) : "-"}
                  compact
                />
                <Metric
                  label="Loss"
                  value={
                    selectedMove?.cpLoss == null
                      ? "-"
                      : `${selectedMove.cpLoss.toFixed(0)} cp`
                  }
                  compact
                />
              </div>
            </div>

            <div className="rounded-lg border border-white/10 bg-surface p-4">
              <h3 className="mb-3 text-sm font-medium text-foreground/80">
                Target style signal
              </h3>
              <div className="space-y-2 text-sm">
                <SignalRow label="Quality" value={selectedMove ? QUALITY_LABELS[selectedMove.quality] : "-"} />
                <SignalRow label="Phase" value={selectedMove?.phase ?? "-"} />
                <SignalRow label="Risk" value={selectedMove ? moveSignal(selectedMove) : "-"} />
                <SignalRow label="Best" value={selectedMove?.bestSan ?? selectedMove?.bestUci ?? "-"} />
                <SignalRow label="Baseline" value={`${baseline.brilliantPct.toFixed(1)}%`} />
                <SignalRow label="Tal" value={talBenchmark?.status === "complete" ? `${talBenchmark.brilliantPct.toFixed(1)}%` : "pending"} />
              </div>
              {selectedMove && selectedMove.signals.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {selectedMove.signals.map((signal) => (
                    <SignalBadge key={signal} signal={signal} />
                  ))}
                </div>
              )}
            </div>

            <div className="rounded-lg border border-white/10 bg-surface p-4">
              <h3 className="mb-3 text-sm font-medium text-foreground/80">
                Candidate lines
              </h3>
              <div className="space-y-2">
                {(selectedMove?.pv ?? []).slice(0, 3).map((candidate) => (
                  <div
                    key={`${candidate.rank}-${candidate.uci}`}
                    className="grid grid-cols-[28px_minmax(0,1fr)_64px] items-center gap-2 rounded-md border border-white/10 bg-background/35 px-3 py-2 text-sm"
                  >
                    <span className="text-xs text-foreground/45">#{candidate.rank}</span>
                    <span className="truncate font-mono">
                      {candidate.san ?? candidate.uci ?? "-"}
                    </span>
                    <span className="text-right font-mono text-xs text-foreground/55">
                      {fmtEval(candidate.eval)}
                    </span>
                  </div>
                ))}
                {(!selectedMove || selectedMove.pv.length === 0) && (
                  <div className="rounded-md border border-white/10 bg-background/35 px-3 py-6 text-sm text-foreground/50">
                    No candidate lines stored
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-lg border border-white/10 bg-surface p-4">
              <h3 className="mb-3 text-sm font-medium text-foreground/80">
                Intent
              </h3>
              <div className="mb-3 grid grid-cols-3 gap-2">
                {(["saw", "calculated", "stumbled"] as const).map((state) => (
                  <button
                    key={state}
                    type="button"
                    disabled={!noteKey}
                    onClick={() =>
                      noteKey &&
                      setIntentState((current) => ({
                        ...current,
                        [noteKey]: state,
                      }))
                    }
                    className={`rounded-md border px-2 py-2 text-xs capitalize transition ${
                      currentIntent === state
                        ? "border-accent/60 bg-accent/10 text-accent"
                        : "border-white/10 bg-background/35 text-foreground/60"
                    }`}
                  >
                    {state}
                  </button>
                ))}
              </div>
              <textarea
                value={notesForMove}
                disabled={!noteKey}
                onChange={(event) =>
                  noteKey &&
                  setIntentNotes((current) => ({
                    ...current,
                    [noteKey]: event.target.value,
                  }))
                }
                className="min-h-28 w-full resize-y rounded-md border border-white/10 bg-background/50 px-3 py-2 text-sm outline-none focus:border-accent/50 disabled:opacity-50"
                placeholder="What was the idea?"
              />
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
}

function Metric({
  label,
  value,
  compact = false,
}: {
  label: string;
  value: string;
  compact?: boolean;
}) {
  return (
    <div
      className={`rounded-md border border-white/10 bg-surface-elevated/55 ${
        compact ? "px-3 py-2" : "px-4 py-3"
      }`}
    >
      <div className="text-xs uppercase tracking-[0.14em] text-foreground/40">
        {label}
      </div>
      <div className="mt-1 truncate text-lg font-semibold">{value}</div>
    </div>
  );
}

function Badge({ label }: { label: string }) {
  return (
    <span className="rounded border border-white/10 bg-background/40 px-2 py-1 text-xs text-foreground/55">
      {label}
    </span>
  );
}

function SignalBadge({
  signal,
  suffix,
}: {
  signal: MoveSignal;
  suffix?: string;
}) {
  return (
    <span
      className={`w-fit rounded border px-2 py-1 text-xs ${
        SIGNAL_STYLES[signal] ??
        "border-white/10 bg-background/40 text-foreground/55"
      }`}
    >
      {SIGNAL_LABELS[signal] ?? signal}
      {suffix ? ` ${suffix}` : ""}
    </span>
  );
}

function SignalRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-white/5 py-2 last:border-b-0">
      <span className="text-foreground/45">{label}</span>
      <span className="text-right font-medium">{value}</span>
    </div>
  );
}
