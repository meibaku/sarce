"use client";

import { useEffect, useState } from "react";
import { getGameIdeas } from "@/lib/api";
import type { GameDetail, GameIdeas, IdeaFamily, IdeaVerdict, MotifTag } from "@/types/chess";

const FAMILY_LABELS: Record<IdeaFamily, string> = {
  gambit: "Gambit",
  king_attack: "King attack",
  squeeze: "Squeeze",
};

// Describes what happened to the idea, not how well the player did.
const VERDICT_LABELS: Record<IdeaVerdict, string> = {
  worked: "Landed",
  refuted: "Answered by your opponent",
  fizzled: "Faded out",
};

const VERDICT_STYLES: Record<IdeaVerdict, string> = {
  worked: "border-emerald-400/40 bg-emerald-400/10 text-emerald-200",
  refuted: "border-amber-300/40 bg-amber-400/10 text-amber-100",
  fizzled: "border-white/15 bg-white/5 text-foreground/70",
};

const MOTIF_LABELS: Record<MotifTag, string> = {
  sacrifice: "Sacrifice",
  fork: "Fork",
  pin: "Pin",
  skewer: "Skewer",
  discovered_attack: "Discovered attack",
  hanging_piece: "Piece left loose",
};

interface IdeasPanelProps {
  game: GameDetail | null;
  selectedPly: number | null;
  onSelectPly: (ply: number) => void;
  refreshToken: number;
}

function moveNumber(ply: number) {
  return Math.floor(ply / 2) + 1;
}

export function IdeasPanel({ game, selectedPly, onSelectPly, refreshToken }: IdeasPanelProps) {
  const [data, setData] = useState<GameIdeas | null>(null);
  const gameId = game?.id ?? null;

  useEffect(() => {
    let cancelled = false;
    if (!gameId) {
      setData(null);
      return;
    }
    getGameIdeas(gameId)
      .catch(() => null)
      .then((res) => {
        if (!cancelled) setData(res);
      });
    return () => {
      cancelled = true;
    };
  }, [gameId, refreshToken]);

  if (!game) return null;

  const ideas = data?.ideas ?? [];
  const tags = data?.tags ?? [];
  const yourMotifs = tags.filter((tag) => tag.ply === selectedPly && tag.byUser);
  const theirMotifs = tags.filter(
    (tag) => selectedPly != null && tag.ply === selectedPly - 1 && !tag.byUser,
  );

  /** Idea windows can start on an opponent ply; jump to the user's first move inside. */
  function selectIdea(startPly: number, endPly: number) {
    const move = game?.moves.find((m) => m.ply >= startPly && m.ply <= endPly);
    if (move) onSelectPly(move.ply);
  }

  return (
    <div className="rounded-lg border border-white/10 bg-surface p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-medium text-foreground/80">Ideas</h3>
        <span className="text-xs text-foreground/40">what you were going for</span>
      </div>

      {ideas.length === 0 && tags.length === 0 ? (
        <p className="text-sm text-foreground/50">
          No ideas tagged for this game yet. Tagging runs when the intention tagger
          is enabled on the API.
        </p>
      ) : (
        <div className="space-y-3 text-sm">
          {ideas.length === 0 && (
            <p className="text-foreground/50">No longer plans stood out in this game.</p>
          )}
          {ideas.map((idea) => (
            <button
              key={`${idea.family}-${idea.startPly}`}
              type="button"
              onClick={() => selectIdea(idea.startPly, idea.endPly)}
              className="flex w-full flex-wrap items-center gap-2 rounded-md border border-white/10 bg-background/35 px-3 py-2 text-left transition hover:border-white/25"
            >
              <span className="font-medium">{FAMILY_LABELS[idea.family]}</span>
              <span className="font-mono text-xs text-foreground/45">
                moves {moveNumber(idea.startPly)}–{moveNumber(idea.endPly)}
              </span>
              <span className={`rounded border px-2 py-0.5 text-xs ${VERDICT_STYLES[idea.verdict]}`}>
                {VERDICT_LABELS[idea.verdict]}
              </span>
              {idea.isPivot && (
                <span className="rounded border border-brilliant/50 bg-brilliant/15 px-2 py-0.5 text-xs text-brilliant">
                  Pivot
                </span>
              )}
            </button>
          ))}

          {(yourMotifs.length > 0 || theirMotifs.length > 0) && (
            <div className="space-y-1">
              {yourMotifs.length > 0 && (
                <MotifRow label="This move" motifs={yourMotifs.map((t) => t.tag)} />
              )}
              {theirMotifs.length > 0 && (
                <MotifRow label="Their last move" motifs={theirMotifs.map((t) => t.tag)} />
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function MotifRow({ label, motifs }: { label: string; motifs: MotifTag[] }) {
  return (
    <div className="flex flex-wrap items-center gap-1">
      <span className="mr-1 text-xs text-foreground/45">{label}</span>
      {motifs.map((motif) => (
        <span
          key={motif}
          className="rounded border border-cyan-300/40 bg-cyan-400/10 px-2 py-0.5 text-xs text-cyan-100"
        >
          {MOTIF_LABELS[motif]}
        </span>
      ))}
    </div>
  );
}
