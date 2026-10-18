"use client";

import { use, useEffect, useState } from "react";
import { AppShell } from "@/components/shell/app-shell";
import { SummaryView } from "@/components/summary/summary-view";
import { PrimaryLink } from "@/components/ui/buttons";
import { Card } from "@/components/ui/card";
import { getGameSummary, getSettings, setGameFelt } from "@/lib/api";
import type { SummaryApi } from "@/types/chess";

export default function GameSummaryPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [data, setData] = useState<SummaryApi | null>(null);
  const [failed, setFailed] = useState(false);
  const [ask, setAsk] = useState(true);

  useEffect(() => {
    getGameSummary(id).then(setData).catch(() => setFailed(true));
    getSettings()
      .then((s) => setAsk(s.questionBudget > 0))
      .catch(() => undefined);
  }, [id]);

  return (
    <AppShell title="after the game">
      {data ? (
        <SummaryView data={data} askQuestion={ask} onFelt={(answer) => setGameFelt(id, answer).then(() => undefined)} />
      ) : failed ? (
        <Card className="items-start gap-3">
          <span className="text-[18px] font-medium">This game couldn&apos;t be loaded</span>
          <span className="text-[13px] leading-[1.55] text-ink-2">It may have been removed, or the analysis service is offline.</span>
          <PrimaryLink href="/">Back to Home</PrimaryLink>
        </Card>
      ) : (
        <div className="h-[2px] w-1/3 animate-pulse bg-accent" role="progressbar" aria-label="Loading" />
      )}
    </AppShell>
  );
}
