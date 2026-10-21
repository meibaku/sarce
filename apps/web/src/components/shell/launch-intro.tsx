"use client";

import { useEffect, useState } from "react";
import { Mascot, useMotionPrefs } from "@/components/ui/mascot";

/*
 * Launch (handoff motion table): the rook traces itself, then says hello, and the overlay fades at
 * 2.9s. Once per browser session. With reduced motion it is a still mark for 1.3s.
 */

const KEY = "sarce.intro.shown";

export function LaunchIntro() {
  const prefs = useMotionPrefs();
  const [phase, setPhase] = useState<"off" | "trace" | "hello" | "fade">("off");

  useEffect(() => {
    if (!prefs) return;
    try {
      if (sessionStorage.getItem(KEY)) return;
      sessionStorage.setItem(KEY, "1");
    } catch {
      return; // no storage (private window): skip the intro rather than replay it every page
    }
    const timers: ReturnType<typeof setTimeout>[] = [];
    setPhase("trace");
    if (prefs.reduced) {
      timers.push(setTimeout(() => setPhase("fade"), 1300));
      timers.push(setTimeout(() => setPhase("off"), 1700));
    } else {
      timers.push(setTimeout(() => setPhase("hello"), 1500));
      timers.push(setTimeout(() => setPhase("fade"), 2900));
      timers.push(setTimeout(() => setPhase("off"), 3300));
    }
    return () => timers.forEach(clearTimeout);
  }, [prefs]);

  if (phase === "off" || !prefs) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-page transition-opacity duration-[400ms]"
      style={{ opacity: phase === "fade" ? 0 : 1 }}
      aria-hidden="true"
    >
      <Mascot state={prefs.reduced ? "static" : phase === "hello" ? "hello" : "trace"} size={104} eyes={phase === "hello"} />
      <span className="text-[28px] font-medium tracking-[-0.02em]">sarce</span>
      <span className="font-mono text-[11px] text-muted">reading your games</span>
    </div>
  );
}
