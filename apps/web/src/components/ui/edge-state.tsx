"use client";

import Link from "next/link";
import { Mascot, useMotionPrefs } from "@/components/ui/mascot";

/*
 * Edge states (handoff screen 11): one 56px line icon (2px stroke), a title, one sentence and one
 * primary action. Every screen uses these instead of spinners or blank pages.
 */

export type EdgeKind = "no-games" | "analysing" | "failed" | "too-few" | "paused" | "offline";

/** The mascot state shown for each edge state once the motion components load. */
const MARK: Record<EdgeKind, string> = {
  "no-games": "empty",
  analysing: "ring",
  failed: "error",
  "too-few": "uncalibrated",
  paused: "quiet",
  offline: "offline",
};

export const EDGE: Record<EdgeKind, { title: string; detail: string; action: string; icon: string; dash?: string }> = {
  "no-games": {
    title: "No games yet",
    detail: "Connect Chess.com or Lichess, or paste a PGN. Your first moments appear while the game is still being read.",
    action: "Connect an account",
    icon: "M8 8h32v32H8z",
    dash: "4 3",
  },
  analysing: {
    title: "Still analysing",
    detail: "Some moments are scored already. Each position takes a few seconds; you can start reading now.",
    action: "Read what's ready",
    icon: "M24 8a16 16 0 1 0 16 16",
  },
  failed: {
    title: "Analysis failed",
    detail: "The engine stopped partway. Your notes are safe. Retry, or open the game in Lichess analysis.",
    action: "Retry",
    icon: "M24 8a16 16 0 1 0 0.1 0M24 16v10M24 31v.5",
  },
  "too-few": {
    title: "Too few games",
    detail: "Numbers appear dashed and stay out of headlines until there are 5.",
    action: "See them anyway",
    icon: "M10 38h28M14 38V22M22 38V16M30 38V26",
    dash: "3 3",
  },
  paused: {
    title: "Tracking paused",
    detail: "Games still sync but aren't counted toward your style.",
    action: "Resume",
    icon: "M19 16v16M29 16v16",
  },
  offline: {
    title: "Offline",
    detail: "Sarce can't reach its analysis service. Your games and notes are safe; start the API and reload.",
    action: "Reload",
    icon: "M8 20q16-14 32 0M14 27q10-9 20 0M20 34q4-4 8 0M8 8l32 32",
  },
};

export function EdgeIcon({ kind }: { kind: EdgeKind }) {
  const e = EDGE[kind];
  return (
    <svg viewBox="0 0 48 48" width={56} height={56} aria-hidden="true" className="text-muted">
      <path d={e.icon} fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={e.dash} />
    </svg>
  );
}

const primary =
  "inline-flex h-10 items-center rounded-[6px] bg-accent px-4 text-[13px] font-medium text-white hover:bg-accent-hover active:bg-accent-active";

export function EdgeState({
  kind,
  detail,
  action,
  href,
  onAction,
}: {
  kind: EdgeKind;
  /** Replaces the default sentence with the real situation ("3 rapid games so far…"). */
  detail?: string;
  action?: string;
  href?: string;
  onAction?: () => void;
}) {
  const e = EDGE[kind];
  const label = action ?? e.action;
  const prefs = useMotionPrefs();
  return (
    <section className="flex flex-col items-center gap-[14px] rounded-[8px] border-[1.5px] border-ink bg-surface px-[22px] py-7 text-center" role="status">
      {prefs ? <Mascot state={MARK[kind]} size={80} /> : <EdgeIcon kind={kind} />}
      <span className="text-[18px] font-medium">{e.title}</span>
      <span className="max-w-[340px] text-[13px] leading-[1.55] text-ink-2">{detail ?? e.detail}</span>
      {href ? (
        <Link href={href} className={primary}>
          {label}
        </Link>
      ) : (
        <button type="button" className={primary} onClick={onAction ?? (() => window.location.reload())}>
          {label}
        </button>
      )}
    </section>
  );
}
