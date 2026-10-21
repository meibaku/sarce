"use client";

import { useState } from "react";
import { PrimaryLink, TextLink } from "@/components/ui/buttons";
import { AutoGrid, SectionLabel } from "@/components/ui/card";
import type { BotId } from "@/types/chess";

/*
 * Play (handoff screen 9). Only against Sarce bots: nothing here runs during a game on another
 * site. Today's intention is saved for the next summary to grade, and never shown mid-game.
 */

export const INTENTS: [string, string][] = [
  ["sacrifice", "Look for a sacrifice"],
  ["calm", "Stay calm when attacked"],
  ["solid", "Just play solid"],
];

export const BOTS: { id: BotId; label: string; why: string }[] = [
  { id: "defender", label: "Defender · 1600", why: "it defends like players at your rating, so your sacrifices meet realistic replies." },
  { id: "tal", label: "Tal-style attacker", why: "it plays the sound move that sets you the hardest problem, the way Tal liked to." },
  { id: "swindler", label: "Swindler", why: "it takes bigger risks to make you find the only move. Good practice for staying calm." },
];

const chip = (on: boolean) =>
  `rounded-[6px] border-[1.5px] px-[10px] py-[6px] text-[12px] font-medium ${
    on ? "border-accent bg-accent-tint text-accent-text" : "border-line-2 bg-surface text-ink hover:bg-panel"
  }`;

export function PlayView({
  intent,
  onIntent,
}: {
  intent: string | null;
  onIntent: (id: string) => void;
}) {
  const [bot, setBot] = useState<BotId>("defender");
  const current = BOTS.find((b) => b.id === bot) ?? BOTS[0];

  return (
    <>
      <div className="flex flex-wrap items-baseline gap-3">
        <h1 className="text-[22px] font-medium">Play</h1>
        <span className="font-mono text-[11px] text-muted">vs Sarce bots only · nothing runs during games on other sites</span>
      </div>

      <AutoGrid min={340} className="items-start">
        <section className="flex flex-col gap-[10px] rounded-[8px] border-[1.5px] border-ink bg-surface p-[18px]">
          <SectionLabel className="!text-accent-text">Today I want to…</SectionLabel>
          <div className="flex flex-col gap-[10px]" role="radiogroup" aria-label="Today I want to">
            {INTENTS.map(([id, label]) => (
              <button
                key={id}
                type="button"
                role="radio"
                aria-checked={intent === id}
                onClick={() => onIntent(id)}
                className={`h-11 rounded-[6px] border-[1.5px] px-[14px] text-left text-[13px] font-medium ${
                  intent === id ? "border-accent bg-accent-tint text-accent-text" : "border-line-2 bg-surface text-ink hover:bg-panel"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <span className="text-[12px] leading-[1.5] text-muted">
            Your next summary grades the game against this first. It&apos;s stored when you leave Sarce and never shown during a game.
          </span>
        </section>

        <section className="flex flex-col gap-[10px] rounded-[8px] border border-line bg-surface p-[18px]">
          <SectionLabel>Warm-up · 2 min · optional</SectionLabel>
          <span className="text-[15px] font-medium">Two positions from this week&apos;s focus</span>
          <span className="text-[13px] leading-[1.5] text-ink-2">One sacrifice you played, one trap at your band. Skippable every time.</span>
          <TextLink href="/train" className="self-start">
            Start warm-up
          </TextLink>
        </section>


        <section className="flex flex-col gap-[10px] rounded-[8px] border border-line bg-surface p-[18px]">
          <SectionLabel>Sarce bot</SectionLabel>
          <div className="flex flex-wrap gap-[6px]" role="radiogroup" aria-label="Sarce bot">
            {BOTS.map((b) => (
              <button key={b.id} type="button" role="radio" aria-checked={bot === b.id} onClick={() => setBot(b.id)} className={chip(bot === b.id)}>
                {b.label}
              </button>
            ))}
          </div>
          <span className="text-[13px] leading-[1.5] text-ink-2">Why this bot: {current.why}</span>
          <PrimaryLink href={`/play/game?bot=${bot}`} className="self-start !px-5">
            Play 3+0
          </PrimaryLink>
        </section>
        {/* After the handoff's three cards: Opponent prep came later, so it doesn't push the bot picker out of place. */}
        <section className="flex flex-col gap-[10px] rounded-[8px] border border-line bg-surface p-[18px]">
          <SectionLabel>Opponent prep · private</SectionLabel>
          <span className="text-[15px] font-medium">Playing someone you know?</span>
          <span className="text-[13px] leading-[1.5] text-ink-2">Their openings and tendencies from finished games only. Only you see it.</span>
          <TextLink href="/prep" className="self-start">
            Prep for an opponent
          </TextLink>
        </section>
      </AutoGrid>
    </>
  );
}
