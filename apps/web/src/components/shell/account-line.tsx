"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getSyncStatus } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import type { SyncStatus } from "@/types/chess";

/** The desktop header's account line: "dratius · Chess.com · synced 2 min ago". */
let cached: Promise<SyncStatus | null> | null = null;

export function AccountLine() {
  const [status, setStatus] = useState<SyncStatus | null>(null);
  useEffect(() => {
    cached ??= getSyncStatus().catch(() => null);
    cached.then(setStatus);
  }, []);
  if (!status) return null;
  const names = [status.chessComUsername, status.lichessUsername].filter(Boolean);
  if (names.length === 0) {
    return (
      <Link href="/settings" className="font-mono text-[11px] text-accent-text hover:underline">
        connect an account
      </Link>
    );
  }
  const sites = [status.chessComUsername ? "Chess.com" : null, status.lichessUsername ? "Lichess" : null].filter(Boolean).join(" + ");
  const synced = status.lastSyncedAt ? `synced ${timeAgo(status.lastSyncedAt)}` : "not synced yet";
  const waiting = status.pending + status.processing;
  return (
    <span className="font-mono text-[11px] text-muted">
      {names[0]} · {sites} · {synced}
      {waiting > 0 ? ` · ${waiting} to analyse` : ""}
    </span>
  );
}
