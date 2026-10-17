"use client";

import { AppShell } from "@/components/shell/app-shell";
import { YouView } from "@/components/you/you-view";
import type { YouApi } from "@/types/chess";

/* Design preview: You with values read off the v1.0 handoff. */

const SAMPLE: YouApi = {
  games: 64,
  goalLo: 6,
  goalHi: 10,
  brilliant: { pct: 4.1, spread: 1.2, weekly: [1.67, 2, 1.33, 2.5, 3, 2.67, 3.67, 3.33, 4.17, 3.83, 4.5, 4.67], from: 2.8, brilliantMoves: 44, yourMoves: 1072 },
  fingerprint: {
    traits: ["Sacrifice", "Chaos", "Calm", "Initiative", "Defence"],
    levels: [
      [2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 7],
      [4, 4, 5, 5, 6, 5, 6, 7, 7, 7, 7, 7],
      [5, 5, 4, 5, 5, 6, 6, 6, 7, 6, 7, 7],
      [3, 4, 4, 4, 5, 5, 6, 6, 6, 7, 7, 7],
      [6, 6, 6, 5, 5, 5, 5, 5, 4, 5, 5, 5],
    ],
    sentence: "More sacrifice and initiative, with defence holding steady.",
  },
  axes: [
    { name: "Sacrifice rate", you: 34 },
    { name: "Chaos created", you: 52 },
    { name: "Calm under fire", you: 61 },
    { name: "Initiative kept", you: 47 },
  ],
  timeControls: [
    { class: "bullet", games: 64, pct: 4.1, spread: 1.2, calibrated: true },
    { class: "blitz", games: 0, pct: null, spread: null, calibrated: false },
    { class: "rapid", games: 0, pct: null, spread: null, calibrated: false },
  ],
  survival: { gameId: "preview", ply: 45, opponent: "m_volkov", moveNumber: 23, survived: true, reply: "Qe2", pFail: 0.55, clock: "0:22", timeControl: "1+0", trapsSurvived: 0.62 },
  sacrifices: { played: 6, held: 4, withNotes: 2 },
};

export default function PreviewYou() {
  return (
    <AppShell title="you" account="kestrel_9 · Chess.com + Lichess · synced 2 min ago">
      <YouView data={SAMPLE} />
    </AppShell>
  );
}
