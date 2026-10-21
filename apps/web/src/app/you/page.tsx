"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/shell/app-shell";
import { EdgeState } from "@/components/ui/edge-state";
import { ChaosMapCard } from "@/components/you/chaos-map";
import { YouView } from "@/components/you/you-view";
import { getYou } from "@/lib/api";
import type { YouApi } from "@/types/chess";

export default function YouPage() {
  const [data, setData] = useState<YouApi | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    getYou().then(setData).catch(() => setFailed(true));
  }, []);

  return (
    <AppShell title="you">
      {data && data.games > 0 ? (
        <YouView data={data} />
      ) : data || failed ? (
        failed ? (
          <EdgeState kind="offline" />
        ) : (
          <EdgeState kind="too-few" detail="Once a few games are analysed, your style fingerprint fills in here." action="Back to Home" href="/" />
        )
      ) : (
        <div className="h-[2px] w-1/3 animate-pulse bg-accent" role="progressbar" aria-label="Loading" />
      )}
      {/* Its own request: the map shows even while the heavier You data is still loading. */}
      <ChaosMapCard />
    </AppShell>
  );
}
