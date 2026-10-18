"use client";

import { useState } from "react";
import { PrimaryButton, TextButton } from "@/components/ui/buttons";
import { AutoGrid } from "@/components/ui/card";
import { Board } from "@/components/ui/board";
import { Mascot } from "@/components/ui/mascot";
import { checkDrillMove } from "@/lib/api";
import type { Confidence, DrillCheck, DrillItem, TrainApi } from "@/types/chess";

/*
 * Train (handoff screen 8). One queue, aimed at the week's focus. Selecting a drill opens it on
 * the board: you play your move on it (click a piece, then a highlighted square) and the server
 * checks it, or you ask for the answer. Afterwards "How sure were you?" schedules it again
 * (tomorrow / 3 days / 9 days).
 */

const CONFIDENCE: [Confidence, string, string][] = [
  ["guessed", "Guessed", "Back tomorrow. Guesses come round quickly."],
  ["unsure", "Unsure", "Back in 3 days."],
  ["sure", "Sure", "Back in 9 days. That one is sticking."],
];

export function TrainView({ data, onAnswer }: { data: TrainApi; onAnswer: (key: string, c: Confidence) => Promise<unknown> }) {
  const [selected, setSelected] = useState(0);
  const [running, setRunning] = useState(false);
  const [revealed, setRevealed] = useState(false);
  const [answered, setAnswered] = useState<Confidence | null>(null);
  const [square, setSquare] = useState<string | null>(null);
  const [check, setCheck] = useState<DrillCheck | null>(null);
  const [checking, setChecking] = useState(false);
  const current: DrillItem | undefined = data.items[selected];

  function open(i: number) {
    setSelected(i);
    setRunning(false);
    setRevealed(false);
    setAnswered(null);
    setSquare(null);
    setCheck(null);
  }

  async function onSquare(sq: string) {
    if (!current || check || checking) return;
    const legal = current.legal ?? [];
    const uci = square ? legal.find((m) => m.startsWith(square + sq)) : undefined;
    if (!uci) {
      setSquare(legal.some((m) => m.startsWith(sq)) ? sq : null);
      return;
    }
    setSquare(null);
    setChecking(true);
    try {
      setCheck(await checkDrillMove(current.fen, uci, current.answer, current.source));
    } catch {
      setCheck(null);
    } finally {
      setChecking(false);
    }
  }

  const targets = square && current ? (current.legal ?? []).filter((m) => m.startsWith(square)).map((m) => m.slice(2, 4)) : [];
  const held = check ? check.matched || check.sound === true : false;

  return (
    <>
      <div className="flex flex-wrap items-baseline gap-3">
        <h1 className="text-[22px] font-medium">One queue</h1>
        <span className="font-mono text-[11px] text-muted">
          {data.focus ? `aimed at this week's focus: ${data.focus.toLowerCase()}` : `${data.waiting} waiting · pick a focus in your weekly recap`}
        </span>
      </div>

      <AutoGrid min={380} className="items-start">
        <section className="overflow-hidden rounded-[8px] border border-line bg-surface">
          {data.items.map((d, i) => (
            <button
              key={d.key}
              type="button"
              onClick={() => open(i)}
              aria-pressed={i === selected}
              className={`grid w-full grid-cols-[24px_minmax(0,1fr)] gap-3 border-t border-hair px-4 py-[14px] text-left first:border-t-0 ${
                i === selected && running ? "bg-accent-tint" : "bg-surface hover:bg-panel"
              }`}
            >
              <span className="pt-[2px] font-mono text-[12px] font-medium text-muted">{i + 1}</span>
              <span className="flex flex-col gap-1">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="rounded-[4px] border border-line-3 px-[7px] py-px font-mono text-[10px] font-medium text-ink-2">{d.source}</span>
                  <span className="font-mono text-[10px] text-faint">{d.meta}</span>
                </span>
                <span className="text-[14px] font-medium">{d.title}</span>
                <span className="text-[12px] text-muted">{d.detail}</span>
              </span>
            </button>
          ))}
        </section>

        {current && (
          <section className="flex flex-col gap-3 rounded-[8px] border-[1.5px] border-ink bg-surface p-[18px]">
            {!running ? (
              <>
                <span className="font-mono text-[11px] text-muted">Up next</span>
                <span className="text-[17px] font-medium">{current.title}</span>
                <span className="text-[13px] leading-[1.5] text-ink-2">{current.detail}</span>
                <PrimaryButton className="self-start !px-5" onClick={() => setRunning(true)}>
                  Start · about 4 min
                </PrimaryButton>
              </>
            ) : (
              <>
                <span className="font-mono text-[11px] text-muted">{current.source}</span>
                <span className="text-[17px] font-medium">{current.title}</span>
                <Board
                  compact
                  fen={check?.fen ?? current.fen}
                  orientation={current.fen.split(" ")[1] === "b" ? "black" : "white"}
                  label="Drill position. Play your move."
                  onSquareClick={check ? undefined : onSquare}
                  selected={square}
                  targets={targets}
                />
                {check ? (
                  <div className="flex flex-col gap-1">
                    <span className={`font-mono text-[13px] font-medium ${held ? "text-sound" : "text-muted"}`}>
                      {check.san} · {check.matched ? "found" : check.sound === true ? "holds" : check.sound === false ? "didn't hold" : "played"}
                    </span>
                    <span className="text-[13px] leading-[1.5] text-ink-2">{check.line}</span>
                    <TextButton className="self-start" onClick={() => setCheck(null)}>
                      Try again
                    </TextButton>
                  </div>
                ) : (
                  <>
                    <span className="text-[12px] text-muted">{checking ? "Checking your move…" : "Your move: click a piece, then a highlighted square."}</span>
                    {current.answer &&
                      (revealed ? (
                        <span className="font-mono text-[13px] text-accent-text">Answer: {current.answer}</span>
                      ) : (
                        <TextButton className="self-start" onClick={() => setRevealed(true)}>
                          Show the answer
                        </TextButton>
                      ))}
                  </>
                )}
                <span className="text-[14px] font-medium">How sure were you?</span>
                <div className="flex gap-[6px]" role="radiogroup" aria-label="How sure were you?">
                  {CONFIDENCE.map(([value, label]) => (
                    <button
                      key={value}
                      type="button"
                      role="radio"
                      aria-checked={answered === value}
                      onClick={async () => {
                        setAnswered(value);
                        await onAnswer(current.key, value);
                      }}
                      className={`h-11 flex-1 rounded-[6px] border-[1.5px] text-[13px] font-medium ${
                        answered === value ? "border-accent bg-accent-tint text-accent-text" : "border-line-2 bg-surface text-ink hover:bg-panel"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                {answered && (
                  <div className="flex items-center gap-3">
                    <Mascot state={answered === "sure" ? "proud" : answered === "unsure" ? "think" : "shake"} size={40} />
                    <span className="text-[13px] text-ink-2">{CONFIDENCE.find(([v]) => v === answered)?.[2]}</span>
                  </div>
                )}
              </>
            )}
          </section>
        )}
      </AutoGrid>
    </>
  );
}
