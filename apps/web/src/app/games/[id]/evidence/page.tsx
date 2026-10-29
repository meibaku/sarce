"use client";

import { Suspense, use } from "react";
import { useSearchParams } from "next/navigation";
import { PilotEvidence } from "@/components/pilot/pilot-evidence";
import { PilotModePage } from "@/components/pilot/pilot-status";
import { AppShell } from "@/components/shell/app-shell";
import { EdgeState } from "@/components/ui/edge-state";

function Evidence({ gameId }: { gameId: string }) {
  const value = Number(useSearchParams().get("ply"));
  const valid = Number.isInteger(value) && value >= 0;
  return <PilotModePage pilot={valid ? <PilotEvidence gameId={gameId} ply={value} /> : <PilotEvidence gameId={gameId} ply={0} />}
    normal={<AppShell title="review"><EdgeState kind="failed" detail="This pilot evidence route is unavailable outside pilot mode." action="Open review" href={`/games/${gameId}/review`} /></AppShell>} />;
}

export default function EvidencePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <Suspense><Evidence gameId={id} /></Suspense>;
}
