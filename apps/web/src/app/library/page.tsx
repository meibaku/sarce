"use client";

import { useEffect, useState } from "react";
import { LibraryView } from "@/components/library/library-view";
import { AppShell } from "@/components/shell/app-shell";
import { EdgeState } from "@/components/ui/edge-state";
import { getSacrifices } from "@/lib/api";
import type { SacrificeRow } from "@/types/chess";

export default function LibraryPage() {
  const [rows, setRows] = useState<SacrificeRow[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    getSacrifices().then((r) => setRows(r.sacrifices)).catch(() => setFailed(true));
  }, []);

  return (
    <AppShell title="your sacrifices">
      {rows && rows.length > 0 ? (
        <LibraryView rows={rows} />
      ) : rows || failed ? (
        failed ? (
          <EdgeState kind="offline" />
        ) : (
          <EdgeState kind="no-games" detail="When you offer material in an analysed game, it's kept here with your note." action="Back to You" href="/you" />
        )
      ) : (
        <div className="h-[2px] w-1/3 animate-pulse bg-accent" role="progressbar" aria-label="Loading" />
      )}
    </AppShell>
  );
}
