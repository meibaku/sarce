"use client";

import { useState } from "react";
import { TextButton } from "@/components/ui/buttons";
import { showToast } from "@/components/ui/toast";
import { createShare } from "@/lib/api";

/*
 * "Share link": makes a read-only page for this summary or sacrifice and copies its address. The page shows
 * a snapshot taken now (no opponent name, no private notes); links can be turned off in Settings.
 */

export function ShareButton({ kind, gameId, ply, label = "Share link" }: { kind: "summary" | "sacrifice"; gameId: string; ply?: number; label?: string }) {
  const [busy, setBusy] = useState(false);
  return (
    <TextButton
      disabled={busy}
      onClick={async () => {
        setBusy(true);
        try {
          const link = await createShare(kind, gameId, ply);
          const url = `${window.location.origin}/s/${link.token}`;
          await navigator.clipboard?.writeText(url).catch(() => undefined);
          showToast("Link copied. Anyone with it can see this page; turn it off in Settings.", "hop");
        } catch {
          showToast("The link couldn't be made. Try again.", "think");
        } finally {
          setBusy(false);
        }
      }}
    >
      {label}
    </TextButton>
  );
}
