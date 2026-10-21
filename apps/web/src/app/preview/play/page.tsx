"use client";

import { useState } from "react";
import { PlayView } from "@/components/play/play-view";
import { AppShell } from "@/components/shell/app-shell";

/* Design preview: Play as in the v1.0 handoff. */
export default function PreviewPlay() {
  const [intent, setIntent] = useState<string | null>("sacrifice");
  return (
    <AppShell title="play" account="kestrel_9 · Chess.com + Lichess · synced 2 min ago">
      <PlayView intent={intent} onIntent={setIntent} />
    </AppShell>
  );
}
