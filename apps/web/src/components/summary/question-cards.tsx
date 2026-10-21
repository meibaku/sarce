"use client";

import { useState } from "react";
import { Card, SectionLabel } from "@/components/ui/card";
import { showToast } from "@/components/ui/toast";
import { answerCheckin, saveMoveIntent } from "@/lib/api";
import type { CheckinAnswer, IntentType, SummaryApi, SummaryQuestion } from "@/types/chess";

/*
 * The intent prompt and the random check-in, the two questions that rotate with "Did this game feel
 * like you?" (docs/DESIGN.md). One ink-outlined card each, same shape as the felt card.
 */

const option =
  "h-11 rounded-[6px] border-[1.5px] px-[14px] text-left text-[13px] font-medium transition-colors duration-[120ms] ease-sarce";

const CHECKIN: [CheckinAnswer, string][] = [
  ["distracted", "Yes, I was distracted"],
  ["time_pressure", "Time pressure"],
  ["on_purpose", "No, I played it on purpose"],
  ["nothing", "Nothing special"],
];

const INTENTS: [IntentType, string][] = [
  ["calculated", "Calculated"],
  ["intuitive", "Intuitive"],
  ["bluff", "Bluff"],
];

export function IntentQuestion({ gameId, q }: { gameId: string; q: Extract<SummaryQuestion, { kind: "intent" }> }) {
  const [type, setType] = useState<IntentType | null>(null);
  const [text, setText] = useState("");
  const [saved, setSaved] = useState(q.answered);
  return (
    <Card lead className="gap-3 !p-[18px]">
      <SectionLabel className="!text-accent-text">This game&apos;s one question</SectionLabel>
      <span className="text-[18px] leading-[1.3] font-medium">
        {q.label}: {q.ask}
      </span>
      {saved ? (
        <span className="text-[13px] leading-[1.5] text-ink-2">Noted. It&apos;s on the moment in your review, next to the engine&apos;s view.</span>
      ) : (
        <>
          <div className="flex flex-wrap gap-[6px]">
            {INTENTS.map(([value, label]) => (
              <button
                key={value}
                type="button"
                aria-pressed={type === value}
                onClick={() => setType(type === value ? null : value)}
                className={`rounded-[6px] border-[1.5px] px-[10px] py-[5px] text-[12px] font-medium ${
                  type === value ? "border-accent bg-accent-tint text-accent-text" : "border-line-2 bg-surface"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            maxLength={2000}
            aria-label="What were you going for?"
            placeholder="What you saw, in your own words."
            className="min-h-14 rounded-[6px] border-[1.5px] border-line-2 px-3 py-[10px] text-[13px] leading-[1.5] placeholder:text-faint"
          />
          <button
            type="button"
            onClick={async () => {
              await saveMoveIntent(gameId, q.ply, { type, note: text });
              setSaved(true);
              showToast("Note saved.", "nod");
            }}
            className="h-10 self-start rounded-[6px] border-[1.5px] border-ink bg-surface px-[14px] text-[13px] font-medium hover:bg-panel active:bg-press"
          >
            Save note
          </button>
        </>
      )}
      <span className="font-mono text-[11px] text-faint">One question per game · the others rotate in</span>
    </Card>
  );
}

export function CheckinQuestion({ gameId, q }: { gameId: string; q: Extract<SummaryQuestion, { kind: "checkin" }> }) {
  const [answer, setAnswer] = useState<CheckinAnswer | null>(q.answer);
  return (
    <Card lead className="gap-3 !p-[18px]">
      <SectionLabel className="!text-accent-text">This game&apos;s one question</SectionLabel>
      <span className="text-[18px] leading-[1.3] font-medium">Was something going on at {q.label}?</span>
      <span className="text-[12px] leading-[1.5] text-muted">
        {q.flagged
          ? "Your pace and choices changed around here. Only you know why."
          : "A random check-in: it tests whether Sarce's flags mean anything."}
      </span>
      <div className="flex flex-col gap-2" role="radiogroup" aria-label="Was something going on?">
        {CHECKIN.map(([value, label]) => (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={answer === value}
            onClick={async () => {
              setAnswer(value);
              await answerCheckin(gameId, q.ply, value, q.flagged);
              showToast("Thanks. That helps Sarce read your games.", "proud");
            }}
            className={`${option} ${answer === value ? "border-accent bg-accent-tint text-accent-text" : "border-line-2 bg-surface hover:bg-panel active:bg-press"}`}
          >
            {label}
          </button>
        ))}
      </div>
      <span className="font-mono text-[11px] text-faint">One question per game · the others rotate in</span>
    </Card>
  );
}

/** "Today I want to…", graded after the game, first. */
export function IntentionResult({ intention }: { intention: NonNullable<SummaryApi["intention"]> }) {
  const tone = intention.met === true ? "text-sound border-sound" : "text-muted border-line-3";
  return (
    <section className="flex flex-wrap items-center gap-3 rounded-[8px] border border-line bg-surface px-[18px] py-3">
      <SectionLabel>Today&apos;s intention</SectionLabel>
      <span className="text-[13px] font-medium">{intention.label}</span>
      <span className={`rounded-[4px] border px-[6px] py-px font-mono text-[10px] font-medium ${tone}`}>
        {intention.met === true ? "met" : intention.met === false ? "not this time" : "no chance to test"}
      </span>
      <span className="basis-full text-[13px] leading-[1.5] text-ink-2">{intention.line}</span>
    </section>
  );
}
