"use client";

import { use, useEffect, useState } from "react";
import { PilotModePage } from "@/components/pilot/pilot-status";
import { PilotStyleRead } from "@/components/pilot/pilot-style-read";
import { AppShell } from "@/components/shell/app-shell";
import { SummaryView } from "@/components/summary/summary-view";
import { EdgeState } from "@/components/ui/edge-state";
import { getGameSummary, getSettings, setGameFelt } from "@/lib/api";
import type { SummaryApi } from "@/types/chess";

function NormalSummary({ id }: { id: string }) {
  const [data, setData] = useState<SummaryApi | null>(null);
  const [failed, setFailed] = useState(false);
  const [ask, setAsk] = useState(true);
  useEffect(() => {
    getGameSummary(id).then(setData).catch(() => setFailed(true));
    getSettings().then((settings) => setAsk(settings.questionBudget > 0)).catch(() => undefined);
  }, [id]);
  return (
    <AppShell title="after the game">
      {data ? <SummaryView data={data} askQuestion={ask} onFelt={(answer) => setGameFelt(id, answer).then(() => undefined)} />
        : failed ? <EdgeState kind="failed" detail="This game couldn't be loaded. It may have been removed, or the analysis service is offline." action="Back to Home" href="/" />
          : <div className="h-[2px] w-1/3 animate-pulse bg-accent" role="progressbar" aria-label="Loading" />}
    </AppShell>
  );
}

export default function GameSummaryPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <PilotModePage normal={<NormalSummary id={id} />} pilot={<PilotStyleRead gameId={id} />} />;
}
