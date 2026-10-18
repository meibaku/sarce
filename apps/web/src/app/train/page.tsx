"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/shell/app-shell";
import { TrainView } from "@/components/train/train-view";
import { EdgeState } from "@/components/ui/edge-state";
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
        failed ? (
          <EdgeState kind="offline" />
        ) : (
          <EdgeState kind="too-few" detail="Drills come back when they're due. Play a game and new ones arrive from it." action="Back to Home" href="/" />
        )
      ) : (
        <div className="h-[2px] w-1/3 animate-pulse bg-accent" role="progressbar" aria-label="Loading" />
      )}
    </AppShell>
  );
}
