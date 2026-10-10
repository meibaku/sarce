"use client";

import { useEffect, useState } from "react";
import { listTraps } from "@/lib/api";
import { PIECES, boardFromFen } from "./chess-replay";
import type { Trap } from "@/types/chess";

const BANDS = [800, 1000, 1200, 1400, 1600, 1800, 2000, 2200];
const FILES = "abcdefgh";

type DrillState = "thinking" | "found" | "revealed";

function squareName(row: number, col: number, flipped: boolean) {
  const file = flipped ? 7 - col : col;
  const rank = flipped ? row + 1 : 8 - row;
  return `${FILES[file]}${rank}`;
}

export function TrapAtlas() {
  const [band, setBand] = useState(1200);
  const [traps, setTraps] = useState<Trap[]>([]);
  const [index, setIndex] = useState(0);
  const [from, setFrom] = useState<string | null>(null);
  const [drill, setDrill] = useState<DrillState>("thinking");
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listTraps(band)
      .catch(() => ({ traps: [] }))
      .then((res) => {
        if (cancelled) return;
        setTraps(res.traps);
        setIndex(0);
      });
    return () => {
      cancelled = true;
    };
  }, [band]);

  const trap = traps[index] ?? null;

  useEffect(() => {
    setFrom(null);
    setDrill("thinking");
    setFeedback(null);
  }, [trap]);

  function handleSquare(square: string) {
    if (!trap || drill !== "thinking") return;
    if (!from) {
      setFrom(square);
      return;
    }
    const attempt = `${from}${square}`;
    setFrom(null);
    // Promotion suffixes are ignored: the first four characters identify the move.
    if (trap.bestReplyUci && trap.bestReplyUci.slice(0, 4) === attempt) {
      setDrill("found");
      setFeedback("That is the safe reply.");
    } else if (trap.commonReplyUci.slice(0, 4) === attempt) {
      setFeedback("That is the move most players choose here — and the one that costs the most.");
    } else {
      setFeedback("Not the safe reply. Try again, or reveal it.");
    }
  }

  const flipped = trap ? trap.fen.split(" ")[1] === "b" : false;
  const rows = trap ? boardFromFen(trap.fen) : [];
  const displayRows = flipped ? [...rows].reverse().map((r) => [...r].reverse()) : rows;

  return (
    <section className="rounded-xl border border-white/10 bg-surface p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-medium">Trap atlas</h2>
          <p className="mt-1 text-sm text-foreground/50">
            Positions where the most common reply at a rating band goes wrong.
          </p>
        </div>
        <label className="text-sm text-foreground/60">
          Rating band{" "}
          <select
            value={band}
            onChange={(event) => setBand(Number(event.target.value))}
            className="ml-2 rounded-md border border-white/15 bg-background px-2 py-1 font-mono"
          >
            {BANDS.map((value) => (
              <option key={value} value={value}>
                {value}–{value + 199}
              </option>
            ))}
          </select>
        </label>
      </div>

      {!trap ? (
        <p className="mt-4 text-sm text-foreground/50">
          No traps collected for this band yet. The atlas fills once the validation
          sampler has been run on real games.
        </p>
      ) : (
        <div className="mt-4 grid gap-5 md:grid-cols-[minmax(0,320px)_1fr]">
          <div className="grid aspect-square grid-cols-8 overflow-hidden rounded-md border border-white/10">
            {displayRows.flatMap((row, r) =>
              row.map((piece, c) => {
                const name = squareName(r, c, flipped);
                const reveal = drill !== "thinking" && trap.bestReplyUci?.slice(2, 4) === name;
                return (
                  <button
                    key={name}
                    type="button"
                    aria-label={name}
                    onClick={() => handleSquare(name)}
                    className={`flex items-center justify-center text-2xl leading-none ${
                      (r + c) % 2 === 0 ? "bg-surface-elevated" : "bg-background"
                    } ${from === name ? "outline outline-2 -outline-offset-2 outline-accent" : ""} ${
                      reveal ? "outline outline-2 -outline-offset-2 outline-emerald-400" : ""
                    }`}
                  >
                    {PIECES[piece] ?? ""}
                  </button>
                );
              }),
            )}
          </div>

          <div className="space-y-3 text-sm">
            <p className="text-foreground/75">
              {flipped ? "Black" : "White"} to move. Click a piece, then its destination, to
              find the safe reply.
            </p>
            <div className="grid grid-cols-3 gap-2">
              <Fact label="Seen" value={`${trap.frequency}×`} />
              <Fact label="Common reply" value={`${Math.round(trap.commonReplyShare * 100)}%`} />
              <Fact label="It costs" value={`${trap.epLoss.toFixed(2)} EP`} />
            </div>
            {feedback && <p className="text-foreground/80">{feedback}</p>}
            {drill !== "thinking" && (
              <p className="font-mono text-foreground/70">
                Safe reply: {trap.bestReplyUci ?? "-"} · common reply: {trap.commonReplyUci}
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setDrill("revealed")}
                disabled={drill !== "thinking"}
                className="rounded-md border border-white/15 px-3 py-1.5 transition hover:border-white/30 disabled:opacity-40"
              >
                Reveal
              </button>
              <button
                type="button"
                onClick={() => setIndex((current) => (current + 1) % traps.length)}
                className="rounded-md border border-accent/40 px-3 py-1.5 text-accent transition hover:border-accent"
              >
                Next trap ({index + 1}/{traps.length})
              </button>
              {trap.eco && (
                <span className="self-center font-mono text-xs text-foreground/45">ECO {trap.eco}</span>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-white/10 bg-background/40 px-3 py-2">
      <p className="text-xs text-foreground/45">{label}</p>
      <p className="font-mono text-base">{value}</p>
    </div>
  );
}
