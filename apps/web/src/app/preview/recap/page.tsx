"use client";

import { RecapView } from "@/components/recap/recap-view";
import { AppShell } from "@/components/shell/app-shell";
import type { RecapApi } from "@/types/chess";

/* Design preview: the weekly recap with the v1.0 handoff's sample week. */

const READS = [30, 50, 22, 72, 40, 62, 10, 80, 50, 30, 90, 62];
const YOU = [false, false, false, true, false, true, false, true, false, false, true, true];

const SAMPLE: RecapApi = {
  week: "Oct 6–12",
  games: 12,
  feltLikeYou: 4,
  bars: READS.map((styleRead, i) => ({ gameId: `preview-${i}`, styleRead, you: YOU[i] })),
  brilliant: { pct: 4.6, spread: 1.8, games: 12, change: 0.5 },
  best: { gameId: "preview", ply: 34, label: "18. Qxh6 !!" },
  lastFocus: { id: "real_problems", label: "Keep setting real problems", line: "Real problems: 3.0 : 1 ✓" },
  streakWeeks: 3,
  focuses: [
    { id: "real_problems", label: "Keep setting real problems" },
    { id: "calm_after_sacrifice", label: "Stay calm after a sacrifice" },
    { id: "safe_reply", label: "Find the safe reply in traps" },
  ],
};

export default function PreviewRecap() {
  return (
    <AppShell title="weekly recap" account="kestrel_9 · Chess.com + Lichess · synced 2 min ago">
      <RecapView data={SAMPLE} onSetFocus={async () => undefined} />
    </AppShell>
  );
}
