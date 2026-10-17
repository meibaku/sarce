"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/shell/app-shell";
import { PrimaryLink } from "@/components/ui/buttons";
import { Card } from "@/components/ui/card";
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
        <Card className="items-start gap-3">
          <span className="text-[18px] font-medium">{failed ? "Sarce can't reach its analysis service" : "Your picture starts with your games"}</span>
          <span className="text-[13px] leading-[1.55] text-ink-2">
            {failed ? "Start the API, then reload." : "Once a few games are analysed, your style fingerprint fills in here."}
          </span>
          <PrimaryLink href="/">Back to Home</PrimaryLink>
        </Card>
      ) : (
        <div className="h-[2px] w-1/3 animate-pulse bg-accent" role="progressbar" aria-label="Loading" />
      )}
    </AppShell>
  );
}
