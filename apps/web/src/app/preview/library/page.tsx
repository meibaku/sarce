"use client";

import { LibraryView } from "@/components/library/library-view";
import { AppShell } from "@/components/shell/app-shell";
import type { SacrificeRow } from "@/types/chess";

/* Design preview: the sacrifice library with the v1.0 handoff's sample rows. */

const row = (label: string, glyph: SacrificeRow["glyph"], type: string, material: number, opponent: string, day: number, held: boolean, note: string | null = null): SacrificeRow => ({
  gameId: "preview", ply: 36, label, glyph, type, material, opponent, playedAt: `2026-10-${String(day).padStart(2, "0")}T12:00:00Z`, held, note,
});

const SAMPLE: SacrificeRow[] = [
  row("19. Rxe5", "!!", "Exchange", 2, "m_volkov", 14, true, "Give the exchange so f7 opens for the bishop and queen."),
  row("22. Bxh7+", "?", "Piece", 3, "Lerato_K", 13, false),
  row("15. Nf5", "!?", "Piece", 3, "dmitri_ok", 11, true),
  row("12. g4", "✓", "Pawn storm", 1, "ana_sicilia", 9, true),
  row("27. Rxf7", "?", "Exchange", 2, "TheBishopKid", 7, false),
  row("18. Qxh6", "!!", "Queen", 9, "m_volkov", 3, true),
];

// Distinct plies so each row has its own key.
const ROWS = SAMPLE.map((r, i) => ({ ...r, ply: i }));

export default function PreviewLibrary() {
  return (
    <AppShell title="your sacrifices" account="kestrel_9 · Chess.com + Lichess · synced 2 min ago">
      <LibraryView rows={ROWS} />
    </AppShell>
  );
}
