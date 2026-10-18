"use client";

import Link from "next/link";
import { useState } from "react";
import { AutoGrid, Card, Dashed, SectionLabel, UncalibratedBadge } from "@/components/ui/card";
import { StyleGauge } from "@/components/ui/style-gauge";
import type { YouApi } from "@/types/chess";

/*
 * You (handoff screen 5). Brilliant is the one big number; tapping it shows how it is counted.
 * References are shown without ranking. A reference player's dot appears only once their games
 * have been scored in the same chaos terms (scripts/process_tal_chaos.py); until then the axes
 * show only you and say so, rather than drawing invented reference dots.
 */

const FP = ["#f5f7fa", "#e6edf6", "#d3e0f0", "#b9cde6", "#97b4d8", "#7096c4", "#4f7ab0", "#2f5f9e"];
const REFS = ["Tal", "Shirov", "Morphy"];

function TrendChart({
  weekly,
  goalLo,
  goalHi,
  changedWeek,
}: {
  weekly: (number | null)[];
  goalLo: number;
  goalHi: number;
  /** Week the Brilliant definition changed (ADR 0004): a dashed "style v2" marker. */
  changedWeek?: number | null;
}) {
  // Same frame as the handoff: the goal band at y 12–36, so 1% = 6 units.
  const scale = 24 / Math.max(1, goalHi - goalLo);
  const y = (pct: number) => 36 - (pct - goalLo) * scale;
  const points = weekly
    .map((v, i) => (v == null ? null : `${(i / Math.max(1, weekly.length - 1)) * 300},${Math.max(2, Math.min(78, y(v)))}`))
    .filter(Boolean) as string[];
  const last = points.at(-1)?.split(",");
  return (
    <svg viewBox="0 0 300 80" className="h-20 w-full overflow-visible" role="img" aria-label="Brilliant % by week against your goal band">
      <rect x="0" y="12" width="300" height="24" fill="var(--accent-tint)" stroke="var(--accent)" strokeWidth="1.25" />
      {points.length > 1 && (
        <polyline points={points.join(" ")} fill="none" stroke="var(--ink)" strokeWidth="1.75" strokeLinejoin="round" strokeLinecap="round" />
      )}
      {changedWeek != null && (
        <>
          <line
            x1={(changedWeek / Math.max(1, weekly.length - 1)) * 300}
            x2={(changedWeek / Math.max(1, weekly.length - 1)) * 300}
            y1="2"
            y2="78"
            stroke="var(--ink)"
            strokeWidth="1"
            strokeDasharray="3 3"
          />
          <text x={(changedWeek / Math.max(1, weekly.length - 1)) * 300 + 4} y="8" fontFamily="var(--font-plex-mono)" fontSize="9" fill="var(--muted)">
            style v2
          </text>
        </>
      )}
      {last && <circle cx={last[0]} cy={last[1]} r="3.5" fill="var(--ink)" />}
      {points.length < 2 && (
        <text x="150" y="62" textAnchor="middle" fontFamily="var(--font-plex-mono)" fontSize="9" fill="var(--faint)">
          the trend fills in as weeks get five games
        </text>
      )}
    </svg>
  );
}

export function YouView({ data }: { data: YouApi }) {
  const [explain, setExplain] = useState(false);
  const [ref, setRef] = useState("Tal");
  const [tc, setTc] = useState<"bullet" | "blitz" | "rapid">(
    data.timeControls.reduce((a, b) => (b.games > a.games ? b : a), data.timeControls[0] ?? { class: "bullet", games: 0 }).class as "bullet",
  );
  const b = data.brilliant;
  const current = data.timeControls.find((t) => t.class === tc);

  return (
    <>
      <div className="flex flex-wrap items-baseline gap-3">
        <h1 className="text-[22px] font-medium">You, as a player</h1>
        <span className="font-mono text-[11px] text-muted">
          {data.games} games · style schema v{data.styleSchema ?? 1} · thresholds v0
        </span>
      </div>

      <AutoGrid min={360}>
        <Card lead className="gap-3 !px-5 !py-[18px]">
          <div className="flex flex-wrap items-baseline gap-[10px]">
            <SectionLabel>Brilliant</SectionLabel>
            {b?.pct != null ? (
              <button
                type="button"
                onClick={() => setExplain((v) => !v)}
                aria-expanded={explain}
                className="border-0 bg-transparent p-0 font-mono text-[32px] text-accent-text hover:underline"
              >
                {b.pct.toFixed(1)}%
              </button>
            ) : (
              <span className="font-mono text-[32px]">
                <Dashed />
              </span>
            )}
            {b?.from != null && <span className="font-mono text-[12px] text-faint">from {b.from.toFixed(1)}% in 12 weeks</span>}
          </div>
          <TrendChart weekly={b?.weekly ?? []} goalLo={data.goalLo} goalHi={data.goalHi} changedWeek={b?.ruleChangedWeek} />
          {explain && b && (
            <div className="rounded-[6px] bg-panel px-3 py-[10px] font-mono text-[12px] leading-[1.6] text-ink-2">
              {b.brilliantMoves} brilliant ÷ {b.yourMoves.toLocaleString()} your moves = {b.pct?.toFixed(1)}%
              <br />
              brilliant = sacrifice · within 0.3 of best · not already winning · not forced
              {b.findRateRule ? " · found by ≤20% at your rating" : ""}
            </div>
          )}
          <span className="text-[12px] text-muted">Tap the number to see how it&apos;s counted.</span>
        </Card>

        <Card className="gap-3 !px-5 !py-[18px]">
          <SectionLabel>Style fingerprint · 12 weeks</SectionLabel>
          {data.fingerprint && (
            <div className="grid grid-cols-[76px_minmax(0,1fr)] gap-1">
              <div className="grid grid-rows-[repeat(5,20px)] items-center gap-1 text-[12px] text-ink-2">
                {data.fingerprint.traits.map((t) => (
                  <span key={t}>{t}</span>
                ))}
              </div>
              <div className="grid grid-cols-12 auto-rows-[20px] gap-1" role="img" aria-label="Style fingerprint by week">
                {data.fingerprint.levels.flatMap((row, r) =>
                  row.map((level, w) => <span key={`${r}-${w}`} className="rounded-[3px]" style={{ background: FP[level] }} />),
                )}
              </div>
            </div>
          )}
          <span className="text-[12px] leading-[1.5] text-muted">{data.fingerprint?.sentence}</span>
        </Card>
      </AutoGrid>

      <Card className="gap-4 !px-5 !py-[18px]">
        <div className="flex flex-wrap items-center gap-[10px]">
          <span className="text-[16px] font-medium">Against your references</span>
          <div className="ml-auto flex gap-[6px]">
            {REFS.map((r) => (
              <button
                key={r}
                type="button"
                aria-pressed={ref === r}
                onClick={() => setRef(r)}
                className={`h-8 rounded-[6px] border-[1.5px] px-3 text-[12px] font-medium ${
                  ref === r ? "border-accent bg-accent-tint text-accent-text" : "border-line-2 bg-surface text-muted"
                }`}
              >
                {r}
              </button>
            ))}
          </div>
        </div>
        {(data.axes ?? []).map((a) => (
          <div key={a.name} className="grid grid-cols-[minmax(90px,140px)_minmax(0,1fr)_36px] items-center gap-[14px]">
            <span className="text-[13px]">{a.name}</span>
            <div className="relative h-6">
              <div className="absolute top-[11px] right-0 left-0 h-[1.5px] bg-line-2" />
              {a.refs?.[ref] != null && (
                <span
                  className="absolute top-1 -ml-2 grid h-4 w-4 place-items-center rounded-full border-[1.5px] border-ink bg-surface font-mono text-[8px] font-medium"
                  style={{ left: `${a.refs[ref]}%` }}
                  aria-label={`${ref}: ${a.refs[ref]}`}
                >
                  {ref[0]}
                </span>
              )}
              {a.you != null && (
                <span
                  className="absolute top-1 -ml-2 h-4 w-4 rounded-full bg-accent"
                  style={{ left: `${a.you}%`, boxShadow: "0 0 0 3px var(--surface)" }}
                />
              )}
            </div>
            <span className="text-right font-mono text-[12px] text-accent-text">{a.you ?? <Dashed />}</span>
          </div>
        ))}
        <span className="font-mono text-[11px] text-muted">
          {data.references?.[ref]
            ? `filled = you · ${ref[0]} = ${ref}, ${data.references[ref].games} games scored the same way · no ranking`
            : `filled = you · ${ref}'s games aren't scored in these terms yet · no ranking`}
        </span>
      </Card>

      <AutoGrid min={300}>
        <Card className="gap-[10px] !px-5 !py-[18px]">
          <SectionLabel>By time control</SectionLabel>
          <div className="flex gap-[6px]">
            {data.timeControls.map((t) => (
              <button
                key={t.class}
                type="button"
                aria-pressed={tc === t.class}
                onClick={() => setTc(t.class)}
                className={`h-8 flex-1 rounded-[6px] border-[1.5px] text-[12px] font-medium capitalize ${
                  tc === t.class ? "border-accent bg-accent-tint text-accent-text" : "border-line-2 bg-surface text-ink"
                }`}
              >
                {t.class}
              </button>
            ))}
          </div>
          {current && (
            <>
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="font-mono text-[22px] text-accent-text">{current.pct != null ? `${current.pct.toFixed(1)}%` : <Dashed />}</span>
                <span className="font-mono text-[11px] text-faint">
                  {current.spread != null ? `±${current.spread.toFixed(1)} · ` : ""}
                  {current.games} game{current.games === 1 ? "" : "s"}
                </span>
                {!current.calibrated && <UncalibratedBadge />}
              </div>
              <StyleGauge compact value={current.pct} goalLo={data.goalLo} goalHi={data.goalHi} />
            </>
          )}
        </Card>

        <Card className="gap-2 !px-5 !py-[18px]">
          <SectionLabel>Survival · the defensive half</SectionLabel>
          {data.survival ? (
            <>
              <Link href={`/games/${data.survival.gameId}/review?ply=${data.survival.ply}`} className="text-[15px] leading-[1.35] font-medium hover:underline">
                Hardest problem you faced lately: move {data.survival.moveNumber} vs {data.survival.opponent ?? "your opponent"}.
              </Link>
              <span className="text-[13px] leading-[1.5] text-ink-2">
                {data.survival.pFail != null ? `${Math.round(data.survival.pFail * 100)}% at your opponent's rating fall for it. ` : ""}
                {data.survival.survived
                  ? `You found the safe reply${data.survival.reply ? `, ${data.survival.reply}` : ""}${data.survival.clock ? `, with ${data.survival.clock} left` : ""}.`
                  : "It didn't hold this time; it's in your Review."}
                {data.survival.trapsSurvived != null ? ` Traps survived: ${Math.round(data.survival.trapsSurvived * 100)}%.` : ""}
              </span>
            </>
          ) : (
            <span className="text-[13px] text-muted">No problems faced yet in the analysed games.</span>
          )}
        </Card>

        <Link
          href="/library"
          className="flex flex-col gap-2 rounded-[8px] border border-line bg-surface px-5 py-[18px] text-left transition-colors duration-[120ms] ease-sarce hover:border-ink"
        >
          <SectionLabel>Your sacrifices</SectionLabel>
          <span className="text-[15px] font-medium">
            {data.sacrifices
              ? `${data.sacrifices.played} played · ${data.sacrifices.held} held · ${data.sacrifices.withNotes} with notes`
              : "None analysed yet"}
          </span>
          <span className="text-[13px] text-accent-text">Open the library →</span>
        </Link>
      </AutoGrid>
    </>
  );
}
