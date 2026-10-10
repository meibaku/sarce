"use client";

import { useEffect, useState } from "react";

export type StyleFocus = "brilliant" | "chaos";

const STORAGE_KEY = "sarce.styleFocus";

const OPTIONS: { value: StyleFocus; label: string; hint: string }[] = [
  { value: "brilliant", label: "Brilliance", hint: "Sound sacrifices — the Tal target" },
  { value: "chaos", label: "Chaos control", hint: "Problems you set, and the ones you solve" },
];

/** The lens the player wants to grow in. Stored on this device; Brilliant % stays the headline. */
export function useStyleFocus(): [StyleFocus, (focus: StyleFocus) => void] {
  const [focus, setFocus] = useState<StyleFocus>("brilliant");

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored === "brilliant" || stored === "chaos") setFocus(stored);
    } catch {
      // Storage can be unavailable (private window); the default still works.
    }
  }, []);

  function update(next: StyleFocus) {
    setFocus(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Not persisted this time; nothing else depends on it.
    }
  }

  return [focus, update];
}

interface StyleFocusPickerProps {
  focus: StyleFocus;
  onChange: (focus: StyleFocus) => void;
}

export function StyleFocusPicker({ focus, onChange }: StyleFocusPickerProps) {
  return (
    <div className="rounded-xl border border-white/10 bg-surface p-4">
      <p className="text-xs uppercase tracking-[0.18em] text-foreground/45">Your focus</p>
      <div className="mt-2 flex flex-wrap gap-2" role="radiogroup" aria-label="Style focus">
        {OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={focus === option.value}
            title={option.hint}
            onClick={() => onChange(option.value)}
            className={`rounded-md border px-3 py-1.5 text-sm transition ${
              focus === option.value
                ? "border-accent/60 bg-accent/10 text-accent"
                : "border-white/15 text-foreground/70 hover:border-white/30"
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>
      <p className="mt-2 text-xs text-foreground/45">
        {OPTIONS.find((option) => option.value === focus)?.hint}. Brilliant % stays your headline.
      </p>
    </div>
  );
}
