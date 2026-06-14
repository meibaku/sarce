"use client";

import type { MainlineMove } from "@/types/chess";

interface ChessReplayProps {
  initialFen: string;
  mainline: MainlineMove[];
  replayIndex: number;
  onReplayIndexChange: (index: number) => void;
  userColor: "white" | "black" | null;
}

const PIECES: Record<string, string> = {
  K: "♔",
  Q: "♕",
  R: "♖",
  B: "♗",
  N: "♘",
  P: "♙",
  k: "♚",
  q: "♛",
  r: "♜",
  b: "♝",
  n: "♞",
  p: "♟",
};

const START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

function boardFromFen(fen: string) {
  const placement = fen.split(" ")[0] ?? "";
  return placement.split("/").map((rank) => {
    const squares: string[] = [];
    for (const char of rank) {
      const empty = Number(char);
      if (Number.isFinite(empty) && empty > 0) {
        squares.push(...Array(empty).fill(""));
      } else {
        squares.push(char);
      }
    }
    return squares;
  });
}

function moveTitle(move: MainlineMove | undefined) {
  if (!move) return "Start";
  const number = Math.floor(move.ply / 2) + 1;
  return `${move.ply % 2 === 0 ? `${number}.` : `${number}...`} ${move.san}`;
}

export function ChessReplay({
  initialFen,
  mainline,
  replayIndex,
  onReplayIndexChange,
  userColor,
}: ChessReplayProps) {
  const safeIndex = Math.min(Math.max(replayIndex, -1), mainline.length - 1);
  const currentMove = safeIndex >= 0 ? mainline[safeIndex] : undefined;
  const fen = (currentMove?.fen ?? initialFen) || START_FEN;
  const board = boardFromFen(fen);
  const flipped = userColor === "black";
  const ranks = flipped ? [...board].reverse() : board;
  const files = flipped
    ? ["h", "g", "f", "e", "d", "c", "b", "a"]
    : ["a", "b", "c", "d", "e", "f", "g", "h"];

  return (
    <div className="rounded-lg border border-white/10 bg-surface p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="text-sm font-medium text-foreground/80">Replay</h3>
        <span className="truncate text-right font-mono text-xs text-foreground/50">
          {moveTitle(currentMove)}
        </span>
      </div>

      <div className="mx-auto grid aspect-square w-full max-w-[320px] grid-cols-8 overflow-hidden rounded-md border border-white/10">
        {ranks.flatMap((rank, rankIndex) =>
          (flipped ? [...rank].reverse() : rank).map((piece, fileIndex) => {
            const dark = (rankIndex + fileIndex) % 2 === 1;
            return (
              <div
                key={`${rankIndex}-${fileIndex}`}
                className={`relative flex items-center justify-center text-3xl leading-none sm:text-4xl ${
                  dark ? "bg-[#6b7f59]" : "bg-[#d7c59a]"
                }`}
              >
                <span
                  className={
                    piece === piece.toUpperCase()
                      ? "text-stone-50 drop-shadow"
                      : "text-stone-950"
                  }
                >
                  {PIECES[piece] ?? ""}
                </span>
                {rankIndex === 7 && (
                  <span className="absolute bottom-0.5 right-1 text-[10px] font-semibold text-black/45">
                    {files[fileIndex]}
                  </span>
                )}
              </div>
            );
          }),
        )}
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2">
        <ReplayButton
          label="Start"
          disabled={!mainline.length || safeIndex <= -1}
          onClick={() => onReplayIndexChange(-1)}
        />
        <ReplayButton
          label="Prev"
          disabled={!mainline.length || safeIndex <= -1}
          onClick={() => onReplayIndexChange(Math.max(-1, safeIndex - 1))}
        />
        <ReplayButton
          label="Next"
          disabled={!mainline.length || safeIndex >= mainline.length - 1}
          onClick={() =>
            onReplayIndexChange(Math.min(mainline.length - 1, safeIndex + 1))
          }
        />
      </div>
    </div>
  );
}

function ReplayButton({
  label,
  disabled,
  onClick,
}: {
  label: string;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="rounded-md border border-white/10 bg-background/35 px-3 py-2 text-xs font-medium text-foreground/65 transition hover:border-white/25 disabled:opacity-40"
    >
      {label}
    </button>
  );
}
