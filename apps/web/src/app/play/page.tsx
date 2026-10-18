"use client";

import { useEffect, useState } from "react";
import { PlayView } from "@/components/play/play-view";
import { AppShell } from "@/components/shell/app-shell";
import { getFocus, setFocus } from "@/lib/api";

export default function PlayPage() {
  const [intent, setIntent] = useState<string | null>(null);

  useEffect(() => {
    getFocus()
      .then((f) => setIntent(f.today))
      .catch(() => undefined);
  }, []);

  return (
    <AppShell title="play">
      <PlayView
        intent={intent}
        onIntent={(id) => {
          setIntent(id);
          setFocus("today", id).catch(() => undefined);
        }}
      />
    </AppShell>
  );
}
