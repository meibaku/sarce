"use client";

import { AppShell } from "@/components/shell/app-shell";
import { SummaryView } from "@/components/summary/summary-view";
import type { SummaryApi } from "@/types/chess";

/* Design preview: Summary with the v1.0 handoff's sample data, for comparison with its screenshots. */

const SAMPLE: SummaryApi = {
  gameId: "preview",
  opponent: "m_volkov",
  result: "win",
  userColor: "white",
  timeControl: "1+0",
  calibrated: true,
  moves: 34,
  headline: "Two real problems set. One sacrifice held.",
  outcome: { kicker: "Brilliant !!", accent: true, text: "19. Rxe5 held. It goes on your timeline." },
  brilliant: { pct: 5.9, count: 1, of: 17, rolling: 4.1, goalLo: 6, goalHi: 10 },
  moments: [
    { ply: 36, san: "Rxe5", glyph: "!!", line: "The exchange sacrifice held", clock: "0:31" },
    { ply: 45, san: "Qh4 → Qe2", glyph: "✓", line: "Trap faced, safe reply found", clock: "0:22" },
    { ply: 52, san: "Kh1", glyph: "?!", line: "Fast move at 2.1 seconds", clock: "0:09" },
  ],
  analysing: false,
  felt: null,
  styleRead: 72,
  styleReadVersion: "v0",
  lichessUrl: "https://lichess.org/analysis",
};

export default function PreviewSummary() {
  return (
    <AppShell title="after the game" account="kestrel_9 · Chess.com + Lichess · synced 2 min ago">
      <SummaryView data={SAMPLE} onFelt={() => undefined} />
    </AppShell>
  );
}
