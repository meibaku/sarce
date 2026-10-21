"use client";

import { useEffect, useRef, useState } from "react";
import { SarceMark } from "@/components/ui/icons";
import { getSettings } from "@/lib/api";

/*
 * The rook mascot and skits (docs/DESIGN.md, motion). Settings decide how much plays:
 * Playful mascot off → no eyes and no skits (the plain mark); Motion reduced (or the system's
 * prefers-reduced-motion when set to "system") → still frames; a quiet week turns skits off.
 * Until the web components load (and on the server) the static mark is drawn in their place.
 */

type Prefs = { playful: boolean; reduced: boolean; quiet: boolean };

let cached: Promise<Prefs> | null = null;

function loadPrefs(): Promise<Prefs> {
  if (!cached) {
    const system = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    cached = getSettings()
      .then((s) => ({ playful: s.playfulMascot, reduced: s.motion === "reduced" || (s.motion === "system" && system), quiet: Boolean(s.quietUntil) }))
      .catch(() => ({ playful: true, reduced: system, quiet: false }));
  }
  return cached;
}

/** Forget cached preferences after Settings change them. */
export function resetMotionPrefs() {
  cached = null;
}

export function useMotionPrefs(): Prefs | null {
  const [prefs, setPrefs] = useState<Prefs | null>(null);
  useEffect(() => {
    let live = true;
    Promise.all([loadPrefs(), import("@/lib/motion/sarce-mark.js"), import("@/lib/motion/sarce-skits.js")]).then(([p]) => {
      if (live) setPrefs(p);
    });
    return () => {
      live = false;
    };
  }, []);
  return prefs;
}

/** Personality states; with the playful mascot off they fall back to the plain mark. */
const MOODS = ["idle", "hello", "nod", "shake", "look", "think", "bow", "cheer", "droop", "sleep", "curious", "proud", "relief", "hop", "shy", "stretch"];

export function Mascot({
  state = "static",
  size = 44,
  eyes = true,
  progress,
  className,
}: {
  /** A mark state (idle, hello, think, brilliant, ring, empty…); see lib/motion/sarce-mark.js. */
  state?: string;
  size?: number;
  eyes?: boolean;
  progress?: number;
  className?: string;
}) {
  const prefs = useMotionPrefs();
  const host = useRef<HTMLSpanElement>(null);
  // Without the playful mascot only the plain mark and its functional states (ring, badges) remain.
  const plain = prefs ? !prefs.playful : false;
  const shown = plain && MOODS.includes(state) ? "static" : state;

  // Built imperatively: React 19 would set JSX props on the custom element as properties, and
  // `size` is a method on <sarce-mark>, so attributes are set here instead.
  useEffect(() => {
    const el = host.current;
    if (!el || !prefs) return;
    let mark = el.querySelector("sarce-mark");
    const attrs: Record<string, string> = {
      state: shown,
      size: String(size),
      eyes: eyes && !plain ? "true" : "false",
      reduced: prefs.reduced ? "true" : "false",
    };
    if (progress != null) attrs.progress = String(progress);
    if (!mark) {
      mark = document.createElement("sarce-mark");
      Object.entries(attrs).forEach(([k, v]) => mark!.setAttribute(k, v));
      el.replaceChildren(mark);
    } else {
      Object.entries(attrs).forEach(([k, v]) => mark!.getAttribute(k) !== v && mark!.setAttribute(k, v));
      if (progress == null) mark.removeAttribute("progress");
    }
  }, [prefs, shown, size, eyes, plain, progress]);

  if (!prefs) return <SarceMark height={size} framed className={className} />;
  return <span ref={host} className={className} style={{ display: "inline-block", lineHeight: 0 }} aria-hidden="true" />;
}

/** A short skit (summary banner, recap streak). Falls back to the mark when skits are off. */
export function Skit({ name, fallbackState = "idle", className }: { name: string; fallbackState?: string; className?: string }) {
  const prefs = useMotionPrefs();
  if (!prefs || !prefs.playful || prefs.quiet) {
    return (
      <div className={`grid place-items-center text-ink ${className ?? ""}`} style={{ aspectRatio: "240 / 140" }}>
        {prefs ? <Mascot state={fallbackState} size={72} /> : <SarceMark height={72} framed />}
      </div>
    );
  }
  return (
    <div className={className} aria-hidden="true">
      <sarce-skit name={name} reduced={prefs.reduced ? "true" : "false"} />
    </div>
  );
}
