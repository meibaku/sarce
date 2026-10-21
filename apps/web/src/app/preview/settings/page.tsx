"use client";

import { useState } from "react";
import { SettingsView } from "@/components/settings/settings-view";
import { AppShell } from "@/components/shell/app-shell";
import type { SettingsApi } from "@/types/chess";

/* Design preview: Settings as in the v1.0 handoff. */
export default function PreviewSettings() {
  const [data, setData] = useState<SettingsApi>({
    goalLo: 6, goalHi: 10, questionBudget: 1, quietUntil: null, sources: "both", theme: "light", playfulMascot: true, motion: "full",
    kept: { games: 64, notes: 23 },
  });
  return (
    <AppShell title="settings" account="kestrel_9 · Chess.com + Lichess · synced 2 min ago">
      <SettingsView data={data} brilliant={4.1} onExport={() => undefined} onChange={(c) => setData({ ...data, ...c })} />
    </AppShell>
  );
}
