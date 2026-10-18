"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { BOTS } from "@/components/play/play-view";
import { PrimaryLink, TextButton } from "@/components/ui/buttons";
import { AutoGrid, SectionLabel } from "@/components/ui/card";
import { Board } from "@/components/ui/board";
import { playBotMove, startBotGame } from "@/lib/api";
import type { BotId, BotPosition } from "@/types/chess";

/*
 * A 3+0 game against a Sarce bot. You play White. The server is stateless: each move sends the
 * position and gets back the bot's reply with the new legal moves. The bot's thinking time comes
 * off its own clock. Click a piece, then a highlighted square.
 */

const START_MS = 180_000;

function clock(ms: number) {
  const s = Math.max(0, Math.ceil(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

type Result = { text: string; detail: string } | null;

export function BotGame({ bot }: { bot: BotId }) {
  const label = BOTS.find((b) => b.id === bot)?.label ?? "Sarce bot";
  const [pos, setPos] = useState<BotPosition | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [moves, setMoves] = useState<string[]>([]);
  const [mine, setMine] = useState(START_MS);
  const [theirs, setTheirs] = useState(START_MS);
  const [thinking, setThinking] = useState(false);
  const [result, setResult] = useState<Result>(null);
  const [started, setStarted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const last = useRef(Date.now());

  useEffect(() => {
    startBotGame().then(setPos).catch(() => setError("Sarce can't reach its analysis service."));
  }, []);

  // One clock runs at a time, from your first move: yours on your move, the bot's while it thinks.
  useEffect(() => {
    if (!pos || result || !started) return;
    last.current = Date.now();
    const id = setInterval(() => {
      const now = Date.now();
      const spent = now - last.current;
      last.current = now;
      if (thinking) setTheirs((t) => t - spent);
      else setMine((m) => m - spent);
    }, 200);
    return () => clearInterval(id);
  }, [pos, thinking, result, started]);

  useEffect(() => {
    if (result) return;
    if (mine <= 0) setResult({ text: "Flagged", detail: "Your clock ran out. The position still goes to your review." });
    else if (theirs <= 0) setResult({ text: "You won on time", detail: `${label} ran out of clock.` });
  }, [mine, theirs, result, label]);

  const finish = useCallback(
    (p: BotPosition, movedLast: "you" | "bot") => {
      if (p.status === "checkmate")
        setResult(movedLast === "you" ? { text: "Checkmate. You won", detail: `Against ${label}.` } : { text: "Checkmated", detail: "Worth a look in your review." });
      else if (p.status !== "ongoing") setResult({ text: "Draw", detail: p.status === "stalemate" ? "Stalemate." : "Drawn position." });
    },
    [label],
  );

  async function onSquare(sq: string) {
    if (!pos || thinking || result || pos.turn !== "white") return;
    const from = selected;
    if (from && pos.legal.some((m) => m.startsWith(from + sq))) {
      setSelected(null);
      setStarted(true);
      setThinking(true);
      try {
        const uci = pos.legal.find((m) => m.startsWith(from + sq)) ?? from + sq;
        // Your move first, so the board updates at once; then the bot's reply.
        const after = await playBotMove(pos.fen, uci, bot, { reply: false });
        setMoves((ms) => [...ms, after.playerSan ?? uci]);
        setPos(after);
        if (after.status !== "ongoing") {
          finish(after, "you");
          return;
        }
        const next = await playBotMove(after.fen, null, bot);
        if (next.botSan) setMoves((ms) => [...ms, next.botSan as string]);
        setPos(next);
        finish(next, "bot");
      } catch {
        setError("That move didn't go through. Try again.");
      } finally {
        setThinking(false);
      }
      return;
    }
    setSelected(pos.legal.some((m) => m.startsWith(sq)) ? sq : null);
  }

  const targets = selected && pos ? pos.legal.filter((m) => m.startsWith(selected)).map((m) => m.slice(2, 4)) : [];

  return (
    <>
      <div className="flex flex-wrap items-baseline gap-3">
        <h1 className="text-[22px] font-medium">vs {label}</h1>
        <span className="font-mono text-[11px] text-muted">3+0 · you play White · Sarce bots only</span>
      </div>
      {error && <p className="text-[13px] text-ink-2">{error}</p>}
      <AutoGrid min={400} className="items-start">
        <div className="flex flex-col gap-[10px]">
          <div className="flex justify-between font-mono text-[13px]">
            <span className={thinking ? "text-accent-text" : "text-muted"}>
              {label} {clock(theirs)}
              {thinking ? " · thinking" : ""}
            </span>
          </div>
          {pos && <Board fen={pos.fen} onSquareClick={onSquare} selected={selected} targets={targets} label="Your game against a Sarce bot" />}
          <div className="flex justify-between font-mono text-[13px]">
            <span className={!thinking && !result ? "text-accent-text" : "text-muted"}>You {clock(mine)}</span>
          </div>
        </div>
        <div className="flex flex-col gap-3 md:gap-[18px]">
          {result ? (
            <section className="flex flex-col items-start gap-3 rounded-[8px] border-[1.5px] border-ink bg-surface p-[18px]">
              <span className="text-[18px] font-medium">{result.text}</span>
              <span className="text-[13px] leading-[1.5] text-ink-2">{result.detail}</span>
              <PrimaryLink href="/play">Back to Play</PrimaryLink>
            </section>
          ) : (
            <section className="flex flex-col gap-2 rounded-[8px] border border-line bg-surface p-[18px]">
              <SectionLabel>Moves</SectionLabel>
              <span className="font-mono text-[13px] leading-[1.7] text-ink-2">
                {moves.length === 0
                  ? "Your move."
                  : moves.map((m, i) => (i % 2 === 0 ? `${i / 2 + 1}. ${m} ` : `${m} `)).join("")}
              </span>
              <TextButton className="self-start !text-muted" onClick={() => setResult({ text: "Resigned", detail: "No harm done. Another one when you're ready." })}>
                Resign
              </TextButton>
            </section>
          )}
        </div>
      </AutoGrid>
    </>
  );
}
