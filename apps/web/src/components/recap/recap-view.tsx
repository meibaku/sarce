"use client";

import Link from "next/link";
import { useState } from "react";
import { PrimaryButton, TextLink } from "@/components/ui/buttons";
import { Dashed, SectionLabel } from "@/components/ui/card";
import { SarceMark } from "@/components/ui/icons";
import type { RecapApi } from "@/types/chess";

/*
 * Weekly recap (handoff screen 7, max width 560). One bar per game of the week; the accent bars
 * felt like you or set a real problem. Choosing next week's focus is the one primary action.
 */

const ORDINAL = ["", "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth"];

export function RecapView({ data, onSetFocus }: { data: RecapApi; onSetFocus: (id: string) => Promise<void> }) {
  const [focus, setFocus] = useState<string>(data.lastFocus?.id ?? data.focuses[0]?.id ?? "");
  const [busy, setBusy] = useState(false);
  const b = data.brilliant;
  const streak =
    data.streakWeeks > 1
      ? `Style streak kept for a ${ORDINAL[data.streakWeeks] ?? `${data.streakWeeks}th`} week.`
      : data.streakWeeks === 1
        ? "A week that counted toward your style."
        : "A quieter week for your style. That happens.";

  return (
    <div className="mx-auto flex w-full max-w-[560px] flex-col gap-4">
      <span className="font-mono text-[11px] text-muted">Weekly recap · {data.week}</span>
      <h1 className="text-[26px] leading-[1.2] font-medium">
        {data.games} game{data.games === 1 ? "" : "s"}, {data.feltLikeYou} that felt like you
      </h1>

      <div className="grid grid-cols-[minmax(0,220px)_minmax(0,1fr)] items-center gap-4 rounded-[8px] border border-line bg-surface pt-2 pr-4 pl-2">
        <div className="flex items-end justify-center gap-3 border-b border-line-2 px-2 pb-1 text-ink" style={{ height: 128 }}>
          {Array.from({ length: Math.max(1, Math.min(3, data.streakWeeks)) }, (_, i) => (
            <SarceMark key={i} height={i === Math.min(3, data.streakWeeks) - 1 ? 52 : 46} framed />
          ))}
        </div>
        <span className="pb-2 text-[14px] leading-[1.5] text-ink-2">{streak}</span>
      </div>

      <div className="flex h-[72px] items-end gap-1 border-b-[1.5px] border-ink pb-1" role="img" aria-label="This week's games by style read">
        {data.bars.map((bar) => (
          <Link
            key={bar.gameId}
            href={`/games/${bar.gameId}`}
            className="flex-1 rounded-t-[2px]"
            style={{ height: `${Math.max(8, bar.styleRead)}%`, background: bar.you ? "var(--accent)" : "var(--line-3)" }}
            aria-label={`Game, style read ${bar.styleRead}%`}
          />
        ))}
      </div>

      <div className="flex items-baseline gap-2">
        <SectionLabel>Brilliant</SectionLabel>
        <span className="font-mono text-[20px] text-accent-text">{b.pct != null ? `${b.pct.toFixed(1)}%` : <Dashed />}</span>
        <span className="font-mono text-[11px] text-faint">
          {b.pct == null
            ? `${b.games} game${b.games === 1 ? "" : "s"} this week · needs 5`
            : [b.spread != null ? `±${b.spread.toFixed(1)}` : null, b.change != null ? `${b.change >= 0 ? "up" : "down"} ${Math.abs(b.change).toFixed(1)}` : null]
                .filter(Boolean)
                .join(" · ")}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-[10px]">
        <div className="flex flex-col gap-[3px] rounded-[6px] border border-line bg-surface p-3">
          <span className="font-mono text-[10px] text-muted">best moment</span>
          {data.best ? (
            <Link href={`/games/${data.best.gameId}/review?ply=${data.best.ply}`} className="font-mono text-[14px] font-medium hover:underline">
              {data.best.label}
            </Link>
          ) : (
            <span className="text-[13px] text-muted">None this week</span>
          )}
        </div>
        <div className="flex flex-col gap-[3px] rounded-[6px] border border-line bg-surface p-3">
          <span className="font-mono text-[10px] text-muted">last focus</span>
          <span className="text-[13px]">{data.lastFocus?.line ?? data.lastFocus?.label ?? "None set yet"}</span>
        </div>
      </div>

      <span className="mt-1 text-[16px] font-medium">Pick next week&apos;s focus</span>
      <div className="flex flex-col gap-4" role="radiogroup" aria-label="Next week's focus">
        {data.focuses.map((f) => (
          <button
            key={f.id}
            type="button"
            role="radio"
            aria-checked={focus === f.id}
            onClick={() => setFocus(f.id)}
            className={`h-11 rounded-[6px] border-[1.5px] px-[14px] text-left text-[13px] font-medium ${
              focus === f.id ? "border-accent bg-accent-tint text-accent-text" : "border-line-2 bg-surface text-ink hover:bg-panel"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-[18px]">
        <PrimaryButton
          className="!px-5"
          disabled={busy || !focus}
          onClick={async () => {
            setBusy(true);
            await onSetFocus(focus);
          }}
        >
          Set focus · start Train
        </PrimaryButton>
        <TextLink href="/" className="!text-muted">
          Keep last week&apos;s
        </TextLink>
      </div>
    </div>
  );
}
