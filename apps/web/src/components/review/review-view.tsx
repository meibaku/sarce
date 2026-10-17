"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { FallsChart, IdeaArcs } from "@/components/review/charts";
import { PrimaryButton, TextButton, TextLink } from "@/components/ui/buttons";
import { AutoGrid, SectionLabel, UncalibratedBadge } from "@/components/ui/card";
import { Board } from "@/components/ui/board";
import { SarceMark } from "@/components/ui/icons";
import { MoveBadge } from "@/components/ui/move-badge";
import type { IntentType, ReviewApi, ReviewMoment } from "@/types/chess";

/*
 * Review (handoff screen 4). The engine's view stays hidden until the player notes their intent
 * or taps "Show the engine": the plan is measured against itself first. Keyboard on desktop:
 * J / K moment, ← → move, N note, E engine.
 */

type NoteState = "closed" | "editing" | "saved" | "skipped";

const INTENTS: [IntentType, string][] = [
  ["calculated", "Calculated"],
  ["intuitive", "Intuitive"],
  ["bluff", "Bluff"],
];

const RESULT = { win: "won", loss: "lost", draw: "drew" } as const;

const outlined =
  "h-10 rounded-[6px] border-[1.5px] border-ink bg-surface px-[14px] text-[13px] font-medium transition-colors duration-[120ms] ease-sarce hover:bg-panel active:bg-press";

export function ReviewView({
  data,
  initialPly,
  onSaveIntent,
}: {
  data: ReviewApi;
  initialPly?: number;
  onSaveIntent: (ply: number, intent: { type: IntentType | null; note: string }) => Promise<unknown>;
}) {
  const startIndex = Math.max(0, data.moments.findIndex((m) => m.ply === initialPly));
  const [index, setIndex] = useState(startIndex);
  const [moments, setMoments] = useState<ReviewMoment[]>(data.moments);
  const [twoMove, setTwoMove] = useState(false);
  const current = moments[index];
  const [viewPly, setViewPly] = useState<number | null>(current?.ply ?? null);
  const [note, setNote] = useState<NoteState>(current?.intent ? "saved" : "closed");
  const [draftType, setDraftType] = useState<IntentType | null>(current?.intent?.type ?? null);
  const [draftText, setDraftText] = useState(current?.intent?.note ?? "");

  const goTo = useCallback(
    (i: number) => {
      const m = moments[i];
      if (!m) return;
      setIndex(i);
      setViewPly(m.ply);
      setNote(m.intent ? "saved" : "closed");
      setDraftType(m.intent?.type ?? null);
      setDraftText(m.intent?.note ?? "");
    },
    [moments],
  );

  const step = useCallback(
    (delta: number) => setViewPly((p) => Math.max(0, Math.min(data.positions.length - 1, (p ?? 0) + delta))),
    [data.positions.length],
  );

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      if (target.closest("input, textarea, [contenteditable]") || e.metaKey || e.ctrlKey || e.altKey) return;
      const actions: Record<string, () => void> = {
        j: () => goTo(Math.min(moments.length - 1, index + 1)),
        k: () => goTo(Math.max(0, index - 1)),
        ArrowRight: () => step(1),
        ArrowLeft: () => step(-1),
        n: () => setNote("editing"),
        e: () => note !== "saved" && setNote("skipped"),
      };
      const action = actions[e.key];
      if (!action) return;
      // Consume the key so "n" does not also land in the note box it opens.
      e.preventDefault();
      action();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [goTo, step, index, moments.length, note]);

  const position = useMemo(() => {
    const p = viewPly == null ? null : data.positions[viewPly];
    return p?.fen ?? data.initialFen;
  }, [viewPly, data.positions, data.initialFen]);

  async function save() {
    if (!current) return;
    const intent = { type: draftType, note: draftText };
    await onSaveIntent(current.ply, intent);
    setMoments((ms) => ms.map((m, i) => (i === index ? { ...m, intent } : m)));
    setNote("saved");
  }

  const meta = [data.timeControl, data.result ? RESULT[data.result] : null, current ? `moment ${index + 1} of ${moments.length}` : null]
    .filter(Boolean)
    .join(" · ");
  const engineShown = note === "saved" || note === "skipped";

  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <SarceMark height={30} framed className="text-ink" />
        <h1 className="text-[20px] font-medium">vs {data.opponent ?? "opponent"}</h1>
        <span className="flex items-center gap-2 font-mono text-[11px] text-muted">
          {meta}
          {!data.calibrated && <UncalibratedBadge />}
        </span>
        <button
          type="button"
          onClick={() => setTwoMove((v) => !v)}
          className="ml-auto h-8 rounded-[6px] border-[1.5px] border-line-2 bg-surface px-3 text-[12px] font-medium hover:bg-panel active:bg-press"
        >
          {twoMove ? "Two-move review" : "Full review"} ▾
        </button>
      </div>

      {moments.length > 0 && (
        <div className="flex flex-wrap gap-[6px]">
          {moments.map((m, i) => (
            <button
              key={m.ply}
              type="button"
              onClick={() => goTo(i)}
              aria-pressed={i === index}
              className={`flex h-[38px] flex-none items-center gap-2 rounded-[19px] border-[1.5px] pr-3 pl-[6px] ${
                i === index ? "border-accent bg-accent-tint" : "border-line bg-surface"
              }`}
            >
              <MoveBadge glyph={m.glyph} />
              <span className="font-mono text-[12px] font-medium">{m.label}</span>
            </button>
          ))}
        </div>
      )}

      <AutoGrid min={400} className="items-start">
        <div className="flex flex-col gap-[10px]">
          <Board
            fen={position}
            orientation={data.userColor ?? "white"}
            hot={current && viewPly === current.ply ? current.hot : []}
            label={current ? `Position after ${current.label}` : "Starting position"}
          />
          {!twoMove && <IdeaArcs ideas={data.ideas} plies={data.positions.length} />}
        </div>

        {current ? (
          <div className="flex flex-col gap-3 md:gap-[18px]">
            <section className="flex flex-col gap-[10px] rounded-[8px] border-[1.5px] border-ink bg-surface px-[18px] py-4">
              <div className="flex items-center gap-[10px]">
                <MoveBadge glyph={current.glyph} size={28} />
                <span className="font-mono text-[16px] font-medium">{current.label}</span>
                {current.clock && <span className="ml-auto font-mono text-[11px] text-muted">clock {current.clock}</span>}
              </div>
              <span className="text-[15px] leading-[1.45]">{current.ask}</span>

              {note === "closed" && (
                <div className="flex flex-col gap-2">
                  <span className="text-[12px] leading-[1.5] text-muted">
                    The engine&apos;s view stays hidden until you note your intent. Your plan is measured against itself.
                  </span>
                  <div className="flex flex-wrap items-center gap-4">
                    <button type="button" className={outlined} onClick={() => setNote("editing")}>
                      I meant this · add a note
                    </button>
                    <TextButton onClick={() => setNote("skipped")}>Show the engine</TextButton>
                  </div>
                </div>
              )}

              {note === "editing" && (
                <div className="flex flex-col gap-2">
                  <div className="flex flex-wrap gap-[6px]" role="radiogroup" aria-label="What kind of move was it?">
                    {INTENTS.map(([value, label]) => (
                      <button
                        key={value}
                        type="button"
                        role="radio"
                        aria-checked={draftType === value}
                        onClick={() => setDraftType(draftType === value ? null : value)}
                        className={`rounded-[6px] border-[1.5px] px-[10px] py-[5px] text-[12px] font-medium ${
                          draftType === value ? "border-accent bg-accent-tint text-accent-text" : "border-line-2 bg-surface"
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  <textarea
                    value={draftText}
                    onChange={(e) => setDraftText(e.target.value)}
                    maxLength={2000}
                    autoFocus
                    placeholder="Give the exchange so f7 opens for the bishop and queen."
                    aria-label="What were you going for?"
                    className="min-h-14 rounded-[6px] border-[1.5px] border-line-2 px-3 py-[10px] text-[13px] leading-[1.5] placeholder:text-faint"
                  />
                  <button type="button" className={`${outlined} self-start`} onClick={save}>
                    Save, then show the engine
                  </button>
                </div>
              )}

              {note === "saved" && current.intent && (
                <div className="flex flex-col gap-[3px] rounded-[6px] bg-panel px-3 py-[10px]">
                  <span className="font-mono text-[10px] text-accent-text">
                    YOU MEANT{current.intent.type ? ` · ${current.intent.type}` : ""}
                  </span>
                  {current.intent.note && <span className="text-[13px] leading-[1.45]">{current.intent.note}</span>}
                  {current.plan && <span className="text-[12px] text-sound">{current.plan}</span>}
                  <TextButton className="self-start !text-[12px] underline" onClick={() => setNote("editing")}>
                    Edit
                  </TextButton>
                </div>
              )}

              {engineShown && (
                <div className="flex flex-col gap-[3px] rounded-[6px] border border-line px-3 py-[10px]">
                  <span className="font-mono text-[10px] text-muted">ENGINE · mirror</span>
                  <span className="text-[13px] leading-[1.45]">{current.mirror}</span>
                </div>
              )}
            </section>

            <section className="flex flex-col gap-[10px] rounded-[8px] border border-line bg-surface px-[18px] py-4">
              <SectionLabel>Who falls for this</SectionLabel>
              {current.pFail && <FallsChart pFail={current.pFail} />}
              <span className="text-[13px] leading-[1.5] text-ink-2">{current.fallsLine}</span>
            </section>

            <div className="flex flex-wrap items-center gap-[18px]">
              <PrimaryButton className="!px-5" onClick={() => goTo((index + 1) % moments.length)}>
                Next moment
              </PrimaryButton>
              <TextLink href="/train">Add to Train</TextLink>
              <TextButton
                onClick={() =>
                  navigator.clipboard?.writeText(
                    `${current.label}: ${current.line}. ${current.fallsLine}${current.intent?.note ? ` My note: ${current.intent.note}` : ""}`,
                  )
                }
              >
                Export
              </TextButton>
            </div>
            <span className="hidden font-mono text-[11px] text-faint md:block">J / K moment · ← → move · N note · E engine</span>
          </div>
        ) : (
          <section className="rounded-[8px] border border-line bg-surface px-[18px] py-4 text-[13px] text-muted">
            No moments stood out in this game. Step through it with ← →.
          </section>
        )}
      </AutoGrid>
    </>
  );
}
