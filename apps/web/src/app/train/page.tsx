"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/shell/app-shell";
import { TrainView } from "@/components/train/train-view";
import { PrimaryLink } from "@/components/ui/buttons";
import { Card } from "@/components/ui/card";
import { answerDrill, getTrain } from "@/lib/api";
import type { TrainApi } from "@/types/chess";

export default function TrainPage() {
  const [data, setData] = useState<TrainApi | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    getTrain().then(setData).catch(() => setFailed(true));
  }, []);

  return (
    <AppShell title="train">
      {data && data.items.length > 0 ? (
        <TrainView data={data} onAnswer={answerDrill} />
      ) : data || failed ? (
        <Card className="items-start gap-3">
          <span className="text-[18px] font-medium">{failed ? "Sarce can't reach its analysis service" : "Nothing due right now"}</span>
          <span className="text-[13px] leading-[1.55] text-ink-2">
            {failed ? "Start the API, then reload." : "Drills come back when they're due. Play a game and new ones arrive from it."}
          </span>
          <PrimaryLink href="/">Back to Home</PrimaryLink>
        </Card>
      ) : (
        <div className="h-[2px] w-1/3 animate-pulse bg-accent" role="progressbar" aria-label="Loading" />
      )}
    </AppShell>
  );
}
