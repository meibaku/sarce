/**
 * The settings the whole app reads (mascot, motion, quiet week), loaded once and refreshed when
 * Settings changes them. Same rules as the web (components/ui/mascot.tsx): Playful mascot off → the
 * still mark; Motion "reduced", or "system" with Reduce Motion on → still poses; a quiet week hides
 * numbers and puts the mascot to sleep.
 */
import { useSyncExternalStore } from "react";
import type { SettingsApi } from "@sarce/types";
import { getSettings } from "@/lib/api";

export type Prefs = { playful: boolean; motion: SettingsApi["motion"]; quietUntil: string | null };

let prefs: Prefs = { playful: true, motion: "system", quietUntil: null };
const listeners = new Set<() => void>();

export function setPrefs(s: Pick<SettingsApi, "playfulMascot" | "motion" | "quietUntil">) {
  prefs = { playful: s.playfulMascot, motion: s.motion, quietUntil: s.quietUntil };
  listeners.forEach((l) => l());
}

export function loadPrefs() {
  return getSettings().then(setPrefs).catch(() => undefined);
}

export function usePrefs(): Prefs {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    () => prefs,
  );
}
