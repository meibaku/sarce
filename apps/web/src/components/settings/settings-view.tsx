"use client";

import { useEffect, useState } from "react";
import { Stepper, Switch, TextLink } from "@/components/ui/buttons";
import { AutoGrid, SectionLabel } from "@/components/ui/card";
import { Mascot } from "@/components/ui/mascot";
import { StyleGauge } from "@/components/ui/style-gauge";
import type { SettingsApi } from "@/types/chess";

/*
 * Settings (handoff screen 10). Every gauge in the app follows the style goal set here. The
 * model card is plain language; "What Sarce keeps" lists only what actually exists.
 */

const pick = (on: boolean) =>
  `rounded-[6px] border-[1.5px] text-[12px] font-medium ${on ? "border-accent bg-accent-tint text-accent-text" : "border-line-2 bg-surface text-ink hover:bg-panel"}`;

function inDays(days: number) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

export function SettingsView({
  data,
  brilliant,
  onExport,
  onChange,
}: {
  data: SettingsApi;
  brilliant: number | null;
  onExport: () => void;
  onChange: (changes: Partial<SettingsApi>) => void;
}) {
  const [systemReduced, setSystemReduced] = useState(false);
  useEffect(() => {
    setSystemReduced(window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }, []);
  const reduced = data.motion === "reduced" || (data.motion === "system" && systemReduced);

  return (
    <>
      <h1 className="text-[22px] font-medium">Settings</h1>
      <AutoGrid min={340} className="items-start">
        <div className="flex flex-col gap-3 md:gap-[18px]">
          <section className="flex flex-col gap-3 rounded-[8px] border-[1.5px] border-ink bg-surface p-[18px]">
            <SectionLabel className="!text-accent-text">Style goal</SectionLabel>
            <span className="text-[13px] leading-[1.5] text-ink-2">Your target Brilliant band. Every gauge in the app follows it.</span>
            <div className="flex flex-wrap items-center gap-x-[18px] gap-y-[10px]">
              <Stepper label="from" value={data.goalLo} min={0} max={data.goalHi - 1} suffix="%" onChange={(v) => onChange({ goalLo: v })} />
              <Stepper label="to" value={data.goalHi} min={data.goalLo + 1} max={15} suffix="%" onChange={(v) => onChange({ goalHi: v })} />
            </div>
            <StyleGauge compact value={brilliant} goalLo={data.goalLo} goalHi={data.goalHi} />
            <span className="font-mono text-[11px] text-muted">references: Tal · change in You</span>
          </section>

          <section className="flex flex-col gap-3 rounded-[8px] border border-line bg-surface p-[18px]">
            <SectionLabel>Questions after a game</SectionLabel>
            <div className="flex flex-wrap gap-[6px]" role="radiogroup" aria-label="Questions after a game">
              {([0, 1, 2] as const).map((n) => (
                <button
                  key={n}
                  type="button"
                  role="radio"
                  aria-checked={data.questionBudget === n}
                  onClick={() => onChange({ questionBudget: n })}
                  className={`h-9 px-3 ${pick(data.questionBudget === n)}`}
                >
                  {["None", "One per game", "Up to two"][n]}
                </button>
              ))}
            </div>
            <span className="text-[12px] leading-[1.5] text-muted">
              Rotates between &quot;felt like you&quot;, intent and random check-ins. Notifications: after a game, quiet 23:00–08:00.
            </span>
            <div className="flex items-center gap-3 border-t border-hair pt-[10px]">
              <span className="flex flex-1 flex-col gap-[2px]">
                <span className="text-[14px] font-medium">Quiet week</span>
                <span className="text-[12px] text-muted">
                  {data.quietUntil ? `Numbers hidden until ${data.quietUntil}.` : "Hide every number for 7 days."}
                </span>
              </span>
              <Switch label="Quiet week" on={Boolean(data.quietUntil)} onChange={(on) => onChange({ quietUntil: on ? inDays(7) : null })} />
            </div>
          </section>

          <section className="flex flex-col gap-3 rounded-[8px] border border-line bg-surface p-[18px]">
            <SectionLabel>Sources and theme</SectionLabel>
            <div className="flex gap-[6px]">
              {(
                [
                  ["chess_com", "Chess.com"],
                  ["lichess", "Lichess"],
                  ["both", "Both"],
                ] as const
              ).map(([id, label]) => (
                <button key={id} type="button" aria-pressed={data.sources === id} onClick={() => onChange({ sources: id })} className={`h-[34px] flex-1 ${pick(data.sources === id)}`}>
                  {label}
                </button>
              ))}
            </div>
            <div className="flex gap-[6px]">
              {(
                [
                  ["light", "Light"],
                  ["system", "Match system"],
                ] as const
              ).map(([id, label]) => (
                <button key={id} type="button" aria-pressed={data.theme === id} onClick={() => onChange({ theme: id })} className={`h-[34px] flex-1 ${pick(data.theme === id)}`}>
                  {label}
                </button>
              ))}
            </div>
            <span className="text-[12px] text-muted">Dark theme is planned for v1.1; &quot;Match system&quot; stays light until then.</span>
          </section>
        </div>

        <div className="flex flex-col gap-3 md:gap-[18px]">
          <section className="flex flex-col gap-[10px] rounded-[8px] border border-line bg-surface p-[18px]">
            <SectionLabel>How Sarce reads your games</SectionLabel>
            <span className="text-[13px] leading-[1.55] text-ink-2">
              Stockfish checks whether a move was sound. Maia-2 estimates what players at your rating would find. Together they say how hard a problem
              was, not just whether it was right.
            </span>
            <div className="grid grid-cols-[110px_minmax(0,1fr)] gap-x-[10px] gap-y-[6px] text-[12px]">
              <span className="text-muted">Engine</span>
              <span className="font-mono">Stockfish 18</span>
              <span className="text-muted">Human model</span>
              <span className="font-mono">Maia-2 · validated on 1+0</span>
              <span className="text-muted">Style schema</span>
              <span className="font-mono">v1 · sacrifice, sound, not forced</span>
              <span className="text-muted">Thresholds</span>
              <span className="font-mono">v0 · provisional</span>
            </div>
            <span className="text-[12px] font-medium text-accent-text">Validation: 50,516 positions, see docs/VALIDATION.md</span>
          </section>

          <section className="flex flex-col gap-[10px] rounded-[8px] border border-line bg-surface p-[18px]">
            <SectionLabel>What Sarce keeps</SectionLabel>
            <div className="flex flex-col text-[13px]">
              {[
                [`Games · ${data.kept?.games ?? 0}`, "this device"],
                [`Intent notes · ${data.kept?.notes ?? 0}`, "this device"],
              ].map(([what, where]) => (
                <div key={what} className="grid grid-cols-[minmax(0,1fr)_auto] gap-[10px] border-t border-hair py-2">
                  <span>{what}</span>
                  <span className="font-mono text-[11px] text-muted">{where}</span>
                </div>
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-[18px]">
              <button
                type="button"
                onClick={onExport}
                className="inline-flex h-9 items-center rounded-[6px] border-[1.5px] border-ink bg-surface px-[14px] text-[12px] font-medium hover:bg-panel active:bg-press"
              >
                Export journal (Markdown)
              </button>
            </div>
          </section>

          <div className="flex flex-wrap gap-[18px]">
            <TextLink href="/onboarding">Replay onboarding</TextLink>
            <TextLink href="/states">Preview edge states</TextLink>
          </div>
        </div>
      </AutoGrid>

      <section className="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-x-[22px] gap-y-[18px] rounded-[8px] border border-line bg-surface p-[18px]">
        <div className="row-span-3 grid h-[104px] w-24 place-items-center rounded-[8px] bg-page text-ink">
          <Mascot state={data.playfulMascot ? "hello" : "static"} size={80} />
        </div>
        <SectionLabel className="!text-accent-text">Mascot and motion</SectionLabel>
        <div className="flex items-center gap-[14px]">
          <div className="flex flex-1 flex-col gap-[2px]">
            <span className="text-[14px] font-medium">Playful mascot</span>
            <span className="text-[13px] leading-[1.5] text-muted">Eyes, moods and short skits after games. Off keeps the plain mark. Quiet mode turns skits off.</span>
          </div>
          <Switch label="Playful mascot" on={data.playfulMascot} onChange={(on) => onChange({ playfulMascot: on })} />
        </div>
        <div className="flex flex-wrap items-center gap-[14px]">
          <div className="flex flex-[1_1_200px] flex-col gap-[2px]">
            <span className="text-[14px] font-medium">Motion</span>
            <span className="text-[13px] leading-[1.5] text-muted">Reduced shows a still frame of each animation. Follows your system setting by default.</span>
          </div>
          <div className="flex gap-[6px]">
            {(
              [
                ["full", "Full", !reduced],
                ["reduced", "Reduced", reduced],
              ] as const
            ).map(([id, label, on]) => (
              <button key={id} type="button" aria-pressed={on} onClick={() => onChange({ motion: id })} className={`h-9 px-[14px] !text-[13px] ${pick(on)}`}>
                {label}
              </button>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
