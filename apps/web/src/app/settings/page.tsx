"use client";

import { useEffect, useState } from "react";
import { SettingsView } from "@/components/settings/settings-view";
import { SharedLinks } from "@/components/share/shared-links";
import { AppShell } from "@/components/shell/app-shell";
import { resetMotionPrefs } from "@/components/ui/mascot";
import { showToast } from "@/components/ui/toast";
import { downloadJournal, getHome, getSettings, getSyncStatus, syncNow, updateSettings } from "@/lib/api";
import { applyTheme } from "@/lib/theme";
import type { SettingsApi, SyncStatus } from "@/types/chess";

export default function SettingsPage() {
  const [data, setData] = useState<SettingsApi | null>(null);
  const [brilliant, setBrilliant] = useState<number | null>(null);
  const [next, setNext] = useState<{ lo: number; hi: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sync, setSync] = useState<SyncStatus | null>(null);

  useEffect(() => {
    getSettings()
      .then((s) => {
        setData(s);
        applyTheme(s.theme); // the profile's choice wins over this device's copy
      })
      .catch(() => setError("Sarce can't reach its analysis service."));
    getHome()
      .then((h) => {
        setBrilliant(h.brilliant.pct);
        if (h.brilliant.nextLo != null && h.brilliant.nextHi != null) setNext({ lo: h.brilliant.nextLo, hi: h.brilliant.nextHi });
      })
      .catch(() => undefined);
    getSyncStatus().then(setSync).catch(() => undefined);
  }, []);

  return (
    <AppShell title="settings">
      {error && <p className="text-[13px] text-ink-2">{error}</p>}
      {data ? (
        <>
        <SettingsView
          data={data}
          brilliant={brilliant}
          next={next}
          sync={sync}
          onSyncNow={() =>
            syncNow()
              .then(() => showToast("Syncing. New games will be analysed in the background.", "hop"))
              .catch(() => setError("Sync couldn't start. Try again."))
          }
          onExport={() => downloadJournal().catch(() => setError("The journal couldn't be exported. Try again."))}
          onChange={(changes) => {
            const previous = data;
            setData({ ...data, ...changes });
            if (changes.theme) applyTheme(changes.theme);
            updateSettings(changes)
              .then((saved) => {
                resetMotionPrefs();
                // The PUT answer has the stored settings only: keep the read-only facts from the GET.
                setData((d) => ({ ...saved, kept: d?.kept, aiAvailable: d?.aiAvailable }));
                if ("goalLo" in changes || "goalHi" in changes) showToast("Goal changed. Every gauge follows it.", "think");
                else if ("quietUntil" in changes)
                  showToast(changes.quietUntil ? "Quiet week on. Numbers are hidden." : "Quiet week over. Numbers are back.", changes.quietUntil ? "sleep" : "stretch");
              })
              .catch(() => {
                setData(previous);
                setError("That change didn't save. Try again.");
              });
          }}
        />
        <SharedLinks />
        </>
      ) : (
        !error && <div className="h-[2px] w-1/3 animate-pulse bg-accent" role="progressbar" aria-label="Loading" />
      )}
    </AppShell>
  );
}
