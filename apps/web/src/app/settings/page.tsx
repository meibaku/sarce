"use client";

import { useEffect, useState } from "react";
import { SettingsView } from "@/components/settings/settings-view";
import { AppShell } from "@/components/shell/app-shell";
import { resetMotionPrefs } from "@/components/ui/mascot";
import { downloadJournal, getHome, getSettings, updateSettings } from "@/lib/api";
import type { SettingsApi } from "@/types/chess";

export default function SettingsPage() {
  const [data, setData] = useState<SettingsApi | null>(null);
  const [brilliant, setBrilliant] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSettings().then(setData).catch(() => setError("Sarce can't reach its analysis service."));
    getHome().then((h) => setBrilliant(h.brilliant.pct)).catch(() => undefined);
  }, []);

  return (
    <AppShell title="settings">
      {error && <p className="text-[13px] text-ink-2">{error}</p>}
      {data ? (
        <SettingsView
          data={data}
          brilliant={brilliant}
          onExport={() => downloadJournal().catch(() => setError("The journal couldn't be exported. Try again."))}
          onChange={(changes) => {
            const previous = data;
            setData({ ...data, ...changes });
            updateSettings(changes)
              .then((saved) => {
                resetMotionPrefs();
                setData((d) => ({ ...saved, kept: d?.kept }));
              })
              .catch(() => {
                setData(previous);
                setError("That change didn't save. Try again.");
              });
          }}
        />
      ) : (
        !error && <div className="h-[2px] w-1/3 animate-pulse bg-accent" role="progressbar" aria-label="Loading" />
      )}
    </AppShell>
  );
}
