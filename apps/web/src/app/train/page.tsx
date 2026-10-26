"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/shell/app-shell";
import { PositionSetter } from "@/components/train/position-setter";
import { LearningEvidenceCard } from "@/components/train/learning-evidence-card";
import { TrainView } from "@/components/train/train-view";
import { EdgeState } from "@/components/ui/edge-state";
import { answerDrill, getSettings, getTrain } from "@/lib/api";
import type { TrainApi } from "@/types/chess";

export default function TrainPage() {
  const [data, setData] = useState<TrainApi | null>(null);
  const [failed, setFailed] = useState(false);
  const [aiHelp, setAiHelp] = useState(false);

  useEffect(() => {
    // Read once on mount (no useSearchParams, so the page needs no Suspense boundary).
    const drill = new URLSearchParams(window.location.search).get("drill");
    getTrain(drill).then(setData).catch(() => setFailed(true));
    getSettings()
      .then((s) => setAiHelp(Boolean(s.aiHelp && s.aiAvailable)))
      .catch(() => undefined);
  }, []);

  return (
    <AppShell title="train">
      <LearningEvidenceCard />
      {data && data.items.length > 0
        ? <TrainView data={data} onAnswer={answerDrill} aiHelp={aiHelp} />
        : data || failed
          ? failed
            ? <EdgeState kind="offline" />
            : <div className="flex flex-col gap-4">
                <EdgeState kind="too-few" detail="Drills come back when they're due. Play a game and new ones arrive from it." action="Back to Home" href="/" />
                <PositionSetter aiHelp={aiHelp} />
              </div>
          : <div className="h-[2px] w-1/3 animate-pulse bg-accent" role="progressbar" aria-label="Loading" />}
    </AppShell>
  );
}
