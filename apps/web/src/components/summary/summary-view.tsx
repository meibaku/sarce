"use client";

import Link from "next/link";
import { useState } from "react";
import { PrimaryLink, TextButton, TextLink } from "@/components/ui/buttons";
import { AutoGrid, Card, SectionLabel, UncalibratedBadge } from "@/components/ui/card";
import { Mascot, Skit } from "@/components/ui/mascot";
import { MoveBadge } from "@/components/ui/move-badge";
import { StyleGauge } from "@/components/ui/style-gauge";
import { moveLabel } from "@/lib/format";
import type { FeltAnswer, SummaryApi } from "@/types/chess";

/*
 * After-game Summary (handoff screen 3). One filled button ("Open review"); the outlined
 * "Open review" in the banner and "Done for now" are secondary. The game's one question sits in
 * the ink-outlined card; once answered it shows the style read next to the player's answer.
 */

const FEEL_OPTIONS: [FeltAnswer, string][] = [
  ["yes", "Yes, that was me"],
  ["partly", "Partly"],
  ["no", "Not really"],
];

const FEEL_SAID: Record<FeltAnswer, string> = { yes: "yes", partly: "partly", no: "not really" };

const FEEL_TEXT: Record<FeltAnswer, string> = {
  yes: "Agreed. This game counts fully toward your timeline.",
  partly: "Both views are kept. When you and the score disagree, the timeline shows both instead of picking one.",
  no: "Kept on your timeline but marked as yours-disagreed, so one off-game doesn't skew the trend.",
};

const RESULT = { win: "won", loss: "lost", draw: "drew" } as const;

export function SummaryView({
  data,
  onFelt,
  askQuestion = true,
}: {
  data: SummaryApi;
  onFelt: (answer: FeltAnswer) => Promise<void> | void;
  /** False when the player chose "None" for questions after a game (Settings). */
  askQuestion?: boolean;
}) {
  const [felt, setFelt] = useState<FeltAnswer | null>(data.felt);
  const [editing, setEditing] = useState(data.felt == null);
  const review = `/games/${data.gameId}/review`;
  const meta = [
    data.timeControl,
    data.userColor ? data.userColor[0].toUpperCase() + data.userColor.slice(1) : null,
    `${data.moves} moves`,
    data.opponent ? `vs ${data.opponent}` : null,
    data.result ? RESULT[data.result] : null,
  ]
    .filter(Boolean)
    .join(" · ");
  const b = data.brilliant;

  async function answer(value: FeltAnswer) {
    setFelt(value);
    setEditing(false);
    await onFelt(value);
  }

  return (
    <>
      <div className="flex flex-col gap-1">
        <span className="flex flex-wrap items-center gap-2 font-mono text-[11px] text-muted">
          {meta}
          {!data.calibrated && <UncalibratedBadge />}
        </span>
        <h1 className="text-[24px] leading-[1.25] font-medium text-pretty">{data.headline}</h1>
      </div>

      <section
        className="grid items-center overflow-hidden rounded-[8px] border border-line bg-surface"
        style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 240px), 1fr))" }}
      >
        <div className="w-full max-w-[320px] px-3 pt-2">
          {data.outcome.accent || data.result === "draw" || data.result === "loss" ? (
            <Skit
              name={data.outcome.accent ? "brilliant" : data.result === "draw" ? "draw" : "resign"}
              fallbackState={data.result === "loss" ? "relief" : data.result === "draw" ? "nod" : "proud"}
            />
          ) : (
            <div className="grid place-items-center text-ink" style={{ aspectRatio: "240 / 110" }}>
              <Mascot state="proud" size={72} />
            </div>
          )}
        </div>
        <div className="flex flex-col gap-2 px-5 py-4">
          <SectionLabel className={data.outcome.accent ? "!text-accent-text" : ""}>{data.outcome.kicker}</SectionLabel>
          <span className="text-[16px] leading-[1.4] font-medium text-pretty">{data.outcome.text}</span>
          <div className="flex flex-wrap gap-2">
            <Link
              href={review}
              className="inline-flex h-9 items-center rounded-[6px] border-[1.5px] border-accent bg-surface px-[14px] text-[13px] font-medium text-accent-text transition-colors duration-[120ms] ease-sarce hover:bg-accent-tint"
            >
              Open review
            </Link>
          </div>
        </div>
      </section>

      <AutoGrid min={360} className="items-start">
        <div className="flex flex-col gap-3 md:gap-[18px]">
          <section className="flex flex-col gap-[10px] rounded-[8px] border border-line bg-surface px-[18px] py-4">
            <div className="flex flex-wrap items-baseline gap-2">
              <SectionLabel>Brilliant this game</SectionLabel>
              <span className="font-mono text-[22px] text-accent-text">{b.pct.toFixed(1)}%</span>
              <span className="font-mono text-[11px] text-faint">
                {b.count} of {b.of}
                {b.rolling != null ? ` · rolling ${b.rolling.toFixed(1)}%` : ""}
              </span>
            </div>
            <StyleGauge compact value={b.pct} average={b.rolling ?? undefined} goalLo={b.goalLo} goalHi={b.goalHi} />
          </section>

          <section className="flex flex-col rounded-[8px] border border-line bg-surface">
            {data.analysing && (
              <div className="flex flex-col gap-2 px-4 py-3">
                <div className="h-[2px] w-full overflow-hidden bg-hair">
                  <div className="h-full w-2/3 animate-pulse bg-accent" />
                </div>
                <span className="font-mono text-[11px] text-muted">
                  {data.moments.length} moment{data.moments.length === 1 ? "" : "s"} scored so far · more on the way
                </span>
              </div>
            )}
            {data.moments.map((m) => (
              <Link
                key={m.ply}
                href={`${review}?ply=${m.ply}`}
                className="grid grid-cols-[30px_minmax(0,1fr)_auto] items-center gap-3 border-t border-hair px-4 py-[13px] text-left first:border-t-0 hover:bg-panel"
              >
                <MoveBadge glyph={m.glyph} />
                <span className="flex min-w-0 flex-col gap-[2px]">
                  <span className="font-mono text-[13px] font-medium">{moveLabel(m.ply, m.san)}</span>
                  <span className="text-[13px] text-ink-2">{m.line}</span>
                </span>
                <span className="font-mono text-[11px] text-muted">{m.clock ?? ""}</span>
              </Link>
            ))}
            {data.moments.length === 0 && !data.analysing && (
              <span className="px-4 py-[13px] text-[13px] text-muted">No moments stood out in this game.</span>
            )}
          </section>
        </div>

        {askQuestion && (
        <Card lead className="gap-3 !p-[18px]">
          <SectionLabel className="!text-accent-text">This game&apos;s one question</SectionLabel>
          <span className="text-[18px] leading-[1.3] font-medium">Did this game feel like you?</span>
          {editing || felt == null ? (
            <div className="flex flex-col gap-2">
              {FEEL_OPTIONS.map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => answer(value)}
                  className="h-11 rounded-[6px] border-[1.5px] border-line-2 bg-surface px-[14px] text-left text-[13px] font-medium transition-colors duration-[120ms] ease-sarce hover:bg-panel active:bg-press"
                >
                  {label}
                </button>
              ))}
            </div>
          ) : (
            <div className="flex flex-col gap-[10px]">
              <div className="grid grid-cols-2 gap-2">
                <div className="flex flex-col gap-[2px] rounded-[6px] bg-panel p-[10px]">
                  <span className="font-mono text-[10px] text-muted">style read</span>
                  <span className="font-mono text-[17px]">{data.styleRead}% you</span>
                </div>
                <div className="flex flex-col gap-[2px] rounded-[6px] bg-accent-tint p-[10px]">
                  <span className="font-mono text-[10px] text-accent-text">you said</span>
                  <span className="font-mono text-[17px] text-accent-text">{FEEL_SAID[felt]}</span>
                </div>
              </div>
              <span className="text-[13px] leading-[1.5] text-ink-2">{FEEL_TEXT[felt]}</span>
              <TextButton className="self-start !text-[12px] underline" onClick={() => setEditing(true)}>
                Change
              </TextButton>
            </div>
          )}
          <span className="font-mono text-[11px] text-faint">One question per game · the others rotate in</span>
        </Card>
        )}
      </AutoGrid>

      <div className="flex flex-wrap items-center gap-[18px]">
        <PrimaryLink href={review} className="!px-5">
          Open review
        </PrimaryLink>
        <TextLink href="/" className="!text-muted">
          Done for now
        </TextLink>
        {data.lichessUrl && (
          <a
            href={data.lichessUrl}
            target="_blank"
            rel="noreferrer"
            className="ml-auto font-mono text-[12px] text-accent-text underline"
          >
            Open in Lichess analysis ↗
          </a>
        )}
      </div>
    </>
  );
}
