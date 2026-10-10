"use client";

import { useEffect, useMemo, useState } from "react";
import { getGameLenses } from "@/lib/api";
import type {
  AnalyzedMove,
  ChaosVerdict,
  GameDetail,
  GameLenses,
  SurvivalVerdict,
} from "@/types/chess";

const VERDICT_LABELS: Record<ChaosVerdict | SurvivalVerdict, string> = {
  real_chaos: "Real chaos",
  calculated_risk: "Calculated risk",
  cheap_chaos: "Cheap chaos",
  survived: "Survived",
  missed: "Hard reply missed",
};

const VERDICT_STYLES: Record<ChaosVerdict | SurvivalVerdict, string> = {
  real_chaos: "border-brilliant/50 bg-brilliant/15 text-brilliant",
  calculated_risk: "border-amber-300/40 bg-amber-400/10 text-amber-100",
  cheap_chaos: "border-orange-400/40 bg-orange-400/10 text-orange-100",
  survived: "border-emerald-400/40 bg-emerald-400/10 text-emerald-200",
  missed: "border-pink-400/40 bg-pink-400/10 text-pink-100",
};

const CLOCK_ERROR_MS = 5000;

interface ChaosReviewProps {
  game: GameDetail | null;
  selectedPly: number | null;
  onSelectPly: (ply: number) => void;
  refreshToken: number;
}

function fmtClock(ms: number | null | undefined) {
  if (ms == null) return null;
  const totalSeconds = ms / 1000;
  if (totalSeconds < 10) return `${totalSeconds.toFixed(1)}s`;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = Math.floor(totalSeconds % 60);
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

function moveName(move: AnalyzedMove | undefined, ply: number) {
  const number = Math.floor(ply / 2) + 1;
  const prefix = ply % 2 === 0 ? `${number}.` : `${number}...`;
  return `${prefix} ${move?.san ?? move?.uci ?? ""}`.trim();
}

/** Per-Elo values are stored as JSON, so the keys arrive as strings. */
function curve(values: Record<string, number> | undefined) {
  return Object.entries(values ?? {})
    .map(([elo, value]) => ({ elo: Number(elo), value }))
    .sort((a, b) => a.elo - b.elo);
}

export function ChaosReview({
  game,
  selectedPly,
  onSelectPly,
  refreshToken,
}: ChaosReviewProps) {
  const [lenses, setLenses] = useState<GameLenses | null>(null);
  const gameId = game?.id ?? null;

  useEffect(() => {
    let cancelled = false;
    if (!gameId) {
      setLenses(null);
      return;
    }
    getGameLenses(gameId)
      .catch(() => null)
      .then((res) => {
        if (!cancelled) setLenses(res);
      });
    return () => {
      cancelled = true;
    };
  }, [gameId, refreshToken]);

  const byPly = useMemo(
    () => new Map((lenses?.moves ?? []).map((move) => [move.ply, move.lenses])),
    [lenses],
  );
  const hasChaosData = (lenses?.moves ?? []).some(
    (move) => move.lenses.chaos || move.lenses.survival,
  );
  const peak = Math.max(
    0.1,
    ...(lenses?.moves ?? []).map((move) => move.lenses.chaos?.score ?? 0),
  );

  if (!game) return null;

  const selected = selectedPly == null ? undefined : byPly.get(selectedPly);
  const selectedMove = game.moves.find((move) => move.ply === selectedPly);
  const chaos = selected?.chaos;
  const survival = selected?.survival;
  const clock = selectedPly == null ? null : lenses?.clocksMs?.[selectedPly];
  const lowOnTime = clock != null && clock < CLOCK_ERROR_MS;
  const pFailCurve = curve(chaos?.details.p_fail);

  return (
    <div className="rounded-lg border border-white/10 bg-surface p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-medium text-foreground/80">Chaos lens</h3>
        <span className="text-xs text-foreground/40">practical trouble created</span>
      </div>

      {!hasChaosData ? (
        <p className="text-sm text-foreground/50">
          No chaos data for this game yet. It is collected when position
          evaluations are enabled on the API.
        </p>
      ) : (
        <>
          <div
            className="flex h-8 gap-px overflow-hidden rounded"
            role="group"
            aria-label="Chaos per move"
          >
            {game.moves.map((move) => {
              const entry = byPly.get(move.ply)?.chaos;
              const strength = Math.min(1, (entry?.score ?? 0) / peak);
              return (
                <button
                  key={move.ply}
                  type="button"
                  title={`${moveName(move, move.ply)} — chaos ${(entry?.score ?? 0).toFixed(2)}`}
                  onClick={() => onSelectPly(move.ply)}
                  className={`min-w-[3px] flex-1 transition ${
                    selectedPly === move.ply ? "outline outline-1 outline-accent" : ""
                  }`}
                  style={{
                    backgroundColor: `color-mix(in srgb, var(--brilliant) ${Math.round(
                      strength * 100,
                    )}%, var(--surface-elevated))`,
                  }}
                />
              );
            })}
          </div>

          <div className="mt-4 space-y-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-foreground/70">
                {selectedPly == null ? "-" : moveName(selectedMove, selectedPly)}
              </span>
              {chaos?.verdict && <VerdictBadge verdict={chaos.verdict as ChaosVerdict} />}
              {survival?.verdict && (
                <VerdictBadge verdict={survival.verdict as SurvivalVerdict} />
              )}
              {fmtClock(clock) && (
                <span className="rounded border border-white/15 px-2 py-0.5 font-mono text-xs text-foreground/60">
                  {fmtClock(clock)}
                  {lowOnTime && survival?.verdict === "missed" ? " · clock error" : ""}
                </span>
              )}
            </div>

            {chaos && !chaos.details.decided && (
              <>
                <div className="grid grid-cols-3 gap-2">
                  <Stat label="Chaos" value={(chaos.score ?? 0).toFixed(2)} />
                  <Stat
                    label="Stake"
                    value={
                      chaos.details.elo == null
                        ? "-"
                        : (chaos.details.stake?.[String(chaos.details.elo)] ?? 0).toFixed(2)
                    }
                  />
                  <Stat
                    label="Your cost"
                    value={
                      chaos.details.objective_cost == null
                        ? "-"
                        : chaos.details.objective_cost.toFixed(2)
                    }
                  />
                </div>

                {pFailCurve.length > 0 && (
                  <div>
                    <p className="mb-1 text-xs text-foreground/45">
                      Who falls for it — chance of missing a safe reply, by rating
                    </p>
                    <div className="flex h-20 items-end gap-2">
                      {pFailCurve.map(({ elo, value }) => (
                        <div
                          key={elo}
                          className="flex h-full flex-1 flex-col items-center justify-end gap-1"
                        >
                          <div
                            className="w-full rounded-t bg-brilliant/60"
                            style={{ height: `${Math.max(2, value * 80)}%` }}
                            title={`${Math.round(value * 100)}%`}
                          />
                          <span className="font-mono text-[10px] text-foreground/45">{elo}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {chaos.details.safe_set_complete === false && (
                  <p className="text-xs text-foreground/45">
                    Many replies were close in value here, so the safe set may be incomplete.
                  </p>
                )}
              </>
            )}

            {chaos?.details.decided && (
              <p className="text-foreground/55">
                The game was already decided here, so chaos is not scored.
              </p>
            )}
            {survival && (
              <p className="text-foreground/75">
                {survival.verdict === "survived"
                  ? "Your opponent set a real problem and you found a safe reply."
                  : "Your opponent set a hard problem here — worth a second look."}
              </p>
            )}
            {!chaos && !survival && (
              <p className="text-foreground/50">No lens data for this move.</p>
            )}

            <p className="text-xs text-foreground/40">
              Estimates use an interim human model and are not yet calibrated, so no
              &quot;N in 10 players&quot; claim is shown.
            </p>
          </div>
        </>
      )}
    </div>
  );
}

function VerdictBadge({ verdict }: { verdict: ChaosVerdict | SurvivalVerdict }) {
  return (
    <span className={`rounded border px-2 py-0.5 text-xs ${VERDICT_STYLES[verdict]}`}>
      {VERDICT_LABELS[verdict]}
    </span>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-white/10 bg-background/40 px-3 py-2">
      <p className="text-xs text-foreground/45">{label}</p>
      <p className="font-mono text-base">{value}</p>
    </div>
  );
}
