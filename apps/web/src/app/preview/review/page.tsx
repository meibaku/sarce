"use client";

import { ReviewView } from "@/components/review/review-view";
import { AppShell } from "@/components/shell/app-shell";
import type { ReviewApi } from "@/types/chess";

/* Design preview: Review with the v1.0 handoff's sample position and moments. */

const FEN = "3q1rk1/4bppp/5n2/4R3/2B5/8/5PPP/3Q2K1 w - - 0 1";

const SAMPLE: ReviewApi = {
  gameId: "preview",
  opponent: "m_volkov",
  result: "win",
  userColor: "white",
  timeControl: "1+0",
  calibrated: true,
  initialFen: FEN,
  positions: Array.from({ length: 68 }, (_, ply) => ({ ply, san: "", uci: "", fen: FEN })),
  moments: [
    {
      ply: 36, san: "Rxe5", label: "19. Rxe5", glyph: "!!", line: "The exchange sacrifice held", clock: "0:31", kind: "set",
      ask: "You gave up two points of material. What were you going for?", hot: ["e5", "f7", "f6"],
      pFail: [0.82, 0.71, 0.58, 0.41, 0.26], fallsLine: "At 1600 bullet, about 6 in 10 players miss the only defence here.",
      mirror: "Sound: the position stayed within 0.05 expected points of best. Found by 14% at your rating.", plan: "Your plan happened: f7 fell on move 24.", intent: null,
    },
    {
      ply: 45, san: "Qh4 → Qe2", label: "23. …Qh4 → Qe2", glyph: "✓", line: "Trap faced, safe reply found", clock: "0:22", kind: "survived",
      ask: "Did you see the trap, or was Qe2 instinct?", hot: ["h4", "e2", "f2"], pFail: [0.74, 0.63, 0.55, 0.39, 0.22],
      fallsLine: "55% of players at your rating fall for …Qh4 here. You found Qe2.", mirror: "", plan: null, intent: null,
    },
    {
      ply: 52, san: "Kh1", label: "27. Kh1", glyph: "?!", line: "Fast move at 2.1 seconds", clock: "0:09", kind: "set",
      ask: "Was something going on at this moment?", hot: ["h1", "g1", "g2"], pFail: [0.2, 0.15, 0.1, 0.06, 0.04],
      fallsLine: "A quiet move played very fast. It didn't cost anything; Sarce just wants to check.", mirror: "", plan: null, intent: null,
    },
  ],
  ideas: [
    { family: "king_attack", startPly: 12, endPly: 34, verdict: "worked", isPivot: false },
    { family: "squeeze", startPly: 36, endPly: 50, verdict: "fizzled", isPivot: true },
  ],
};

export default function PreviewReview() {
  return (
    <AppShell title="review · m_volkov" account="kestrel_9 · Chess.com + Lichess · synced 2 min ago">
      <ReviewView data={SAMPLE} onSaveIntent={async () => undefined} />
    </AppShell>
  );
}
