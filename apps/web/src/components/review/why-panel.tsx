"use client";

import { useEffect, useState } from "react";
import { TextButton } from "@/components/ui/buttons";
import { Board } from "@/components/ui/board";
import { SectionLabel } from "@/components/ui/card";
import { getWhy, reportBrilliant, type WhyApi } from "@/lib/api";

/*
 * "Why this move?" (Review). Answers "why this badge?" and "why isn't this Brilliant?" from what Sarce
 * computed: each Brilliant rule as a check with its number, who falls for the problem, and lines you can
 * step through on the board — what you played, the engine's choices, and a sacrifice that would count.
 */

const KIND_TONE: Record<string, string> = {
  played: "border-ink",
  engine: "border-line-2",
  brilliant: "border-accent",
};

export function WhyPanel({ gameId, ply, orientation, onClose }: { gameId: string; ply: number; orientation: "white" | "black"; onClose: () => void }) {
  // The reply belongs to one move: shown only while that move is open, so a late reply can't land on another.
  const [report, setReport] = useState<{ key: string; line: string } | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);
  const moveKey = `${gameId}:${ply}`;
  const reportLine = report?.key === moveKey ? report.line : null;
  const [data, setData] = useState<WhyApi | null>(null);
  const [failed, setFailed] = useState(false);
  const [line, setLine] = useState(0);
  const [step, setStep] = useState(0);

  useEffect(() => {
    let live = true;
    getWhy(gameId, ply)
      .then((d) => live && (setData(d), setLine(0), setStep(1)))
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, [gameId, ply]);

  // ← / → step through the selected line.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!data || (e.target as HTMLElement)?.closest("input, textarea")) return;
      const n = data.lines[line]?.steps.length ?? 0;
      if (e.key === "]") setStep((s) => Math.min(n, s + 1));
      if (e.key === "[") setStep((s) => Math.max(0, s - 1));
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [data, line]);

  if (failed) {
    return (
      <section className="rounded-[8px] border border-line bg-surface p-[18px] text-[13px] text-muted">
        This move hasn&apos;t been analysed yet, so there&apos;s nothing to explain.{" "}
        <TextButton onClick={onClose}>Close</TextButton>
      </section>
    );
  }
  if (!data) return <div className="h-[2px] w-1/3 animate-pulse bg-accent" role="progressbar" aria-label="Working out why" />;

  const current = data.lines[line];
  const chaos = data.chaos;
  const fen = step === 0 || !current ? data.fenBefore : current.steps[step - 1].fen;
  const passed = data.brilliant.filter((c) => c.passed).length;

  return (
    <section className="flex flex-col gap-4 rounded-[8px] border-[1.5px] border-ink bg-surface p-[18px]" aria-label={`Why ${data.label}`}>
      <div className="flex flex-wrap items-baseline gap-3">
        <SectionLabel className="!text-accent-text">Why {data.label}?</SectionLabel>
        <span className="flex-1" />
        <TextButton className="!text-muted" onClick={onClose}>
          Close
        </TextButton>
      </div>
      <p className="text-[15px] leading-[1.45] font-medium">{data.badge}</p>

      <div className="flex flex-col gap-2">
        <span className="text-[13px] font-medium">
          {data.isBrilliant ? "Why it is Brilliant" : "Why it isn't Brilliant"}{" "}
          <span className="font-mono text-[11px] text-muted">
            {passed} of {data.brilliant.length} rules
          </span>
        </span>
        <ul className="flex flex-col gap-[6px]">
          {data.brilliant.map((c) => (
            <li key={c.rule} className="grid grid-cols-[22px_minmax(0,1fr)] gap-2 text-[13px] leading-[1.45]">
              <span aria-label={c.passed ? "passes" : "doesn't pass"} className={`font-mono font-medium ${c.passed ? "text-sound" : "text-faint"}`}>
                {c.passed ? "✓" : "·"}
              </span>
              <span>
                <span className="font-medium">{c.rule}.</span> <span className="text-ink-2">{c.detail}</span>
              </span>
            </li>
          ))}
        </ul>
        {!data.isBrilliant && (
          <div className="flex flex-wrap items-baseline gap-2 text-[12px] text-muted">
            {reportLine ? (
              <span className="text-ink-2">{reportLine}</span>
            ) : data.reported ? (
              <span>You said Chess.com called this Brilliant.</span>
            ) : (
              <>
                <TextButton
                  className="!text-[12px]"
                  onClick={() => {
                    setReportError(null);
                    reportBrilliant(gameId, ply)
                      .then((r) => setReport({ key: moveKey, line: r.line }))
                      .catch(() => setReportError(moveKey));
                  }}
                >
                  Chess.com called this Brilliant
                </TextButton>
                {reportError === moveKey && <span>That didn&apos;t save. Try again.</span>}
              </>
            )}
          </div>
        )}
      </div>

      {chaos && (chaos.pFail || chaos.safeReplies.length > 0) && (
        <div className="flex flex-col gap-2">
          <span className="text-[13px] font-medium">{chaos.faced ? "The problem you faced" : "The problem you set"}</span>
          {chaos.pFail && (
            <div className="flex items-end gap-3" aria-label="How often players miss the safe reply, by rating">
              {chaos.pFail.map((p, i) => (
                <div key={chaos.rungs[i]} className="flex flex-col items-center gap-1">
                  <span className="font-mono text-[10px] text-ink-2">{Math.round(p * 100)}%</span>
                  <div className="w-7 rounded-[2px] bg-accent" style={{ height: `${Math.max(3, p * 48)}px` }} />
                  <span className="font-mono text-[10px] text-muted">{chaos.rungs[i]}</span>
                </div>
              ))}
              <span className="max-w-[220px] text-[12px] leading-[1.45] text-muted">share of players at each rating who miss every safe reply</span>
            </div>
          )}
          {chaos.safeReplies.length > 0 && (
            <span className="text-[12px] text-ink-2">
              Safe replies: <span className="font-mono">{chaos.safeReplies.join(", ")}</span>
            </span>
          )}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-[240px_minmax(0,1fr)]">
        <div className="flex flex-col gap-2">
          <Board compact fen={fen} orientation={orientation} label="The line on the board" />
          <div className="flex items-center gap-2">
            <button type="button" aria-label="Back one move" onClick={() => setStep((s) => Math.max(0, s - 1))} className="h-8 w-8 rounded-[6px] border-[1.5px] border-line-2 text-[13px]">
              ‹
            </button>
            <span className="flex-1 text-center font-mono text-[11px] text-muted">
              {step === 0 ? "before your move" : `${step} / ${current?.steps.length ?? 0}`}
            </span>
            <button type="button" aria-label="Forward one move" onClick={() => setStep((s) => Math.min(current?.steps.length ?? 0, s + 1))} className="h-8 w-8 rounded-[6px] border-[1.5px] border-line-2 text-[13px]">
              ›
            </button>
          </div>
          <span className="font-mono text-[10px] text-faint">[ / ] step through the line</span>
        </div>
        <div className="flex flex-col gap-2">
          {data.lines.map((ln, i) => (
            <button
              key={`${ln.title}-${i}`}
              type="button"
              aria-pressed={i === line}
              onClick={() => {
                setLine(i);
                setStep(1);
              }}
              className={`flex flex-col gap-1 rounded-[6px] border-[1.5px] p-3 text-left ${i === line ? "bg-accent-tint" : "bg-surface hover:bg-panel"} ${KIND_TONE[ln.kind] ?? "border-line-2"}`}
            >
              <span className="flex flex-wrap items-baseline gap-2">
                <span className="text-[13px] font-medium">{ln.title}</span>
                <span className="font-mono text-[11px] text-muted">{ln.eval}</span>
              </span>
              <span className="text-[12px] text-ink-2">{ln.note}</span>
              <span className="flex flex-wrap gap-x-[6px] font-mono text-[12px]">
                {ln.steps.map((s, j) => (
                  <span
                    key={j}
                    role="button"
                    tabIndex={0}
                    onClick={(e) => {
                      e.stopPropagation();
                      setLine(i);
                      setStep(j + 1);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        setLine(i);
                        setStep(j + 1);
                      }
                    }}
                    className={i === line && step === j + 1 ? "rounded-[3px] bg-accent px-1 text-white" : "cursor-pointer"}
                  >
                    {s.san}
                  </span>
                ))}
              </span>
            </button>
          ))}
        </div>
      </div>
      <span className="font-mono text-[10px] text-faint">Evaluations are from your side, in pawns. The engine is a mirror, not a judge.</span>
    </section>
  );
}
