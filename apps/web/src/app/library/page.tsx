"use client";

import { useEffect, useState } from "react";
import { LibraryView } from "@/components/library/library-view";
import { AppShell } from "@/components/shell/app-shell";
import { PrimaryLink } from "@/components/ui/buttons";
import { Card } from "@/components/ui/card";
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
        <Card className="items-start gap-3">
          <span className="text-[18px] font-medium">{failed ? "Sarce can't reach its analysis service" : "No sacrifices yet"}</span>
          <span className="text-[13px] leading-[1.55] text-ink-2">
            {failed ? "Start the API, then reload." : "When you offer material in an analysed game, it's kept here with your note."}
          </span>
          <PrimaryLink href="/you">Back to You</PrimaryLink>
        </Card>
      ) : (
        <div className="h-[2px] w-1/3 animate-pulse bg-accent" role="progressbar" aria-label="Loading" />
      )}
    </AppShell>
  );
}
