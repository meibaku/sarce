"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PilotModePage, usePilotStatus } from "@/components/pilot/pilot-status";
import { PilotShell } from "@/components/pilot/pilot-shell";
import { PilotCard, PilotProgress } from "@/components/pilot/pilot-ui";
import { listGames } from "@/lib/api";

function Progress() {
  const { status } = usePilotStatus();
  const [waiting, setWaiting] = useState(0);
  useEffect(() => { listGames(false, 50).then(({ games }) => setWaiting(games.filter((game) => game.analysisStatus === "complete" && !game.pilotResonance).length)).catch(() => undefined); }, []);
  if (!status) return null;
  const date = (value: string | null) => value ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value)) : "—";
  const counts = [
    { label: "yes", value: status.answers.yes },
    { label: "partly", value: status.answers.partly },
    { label: "no", value: status.answers.no },
    { label: "waiting", value: waiting },
  ];
  return (
    <PilotShell><main className="mx-auto max-w-[1120px] space-y-7 px-5 py-8">
      <div><p className="font-mono text-[11px] text-muted">{date(status.startsAt)} to {date(status.endsAt)}</p><h1 className="pilot-serif mt-2 text-[32px]">Pilot progress</h1></div>
      <PilotCard className="max-w-[820px] space-y-4 border-[1.5px] border-ink p-6"><h2 className="pilot-serif text-[24px]">{status.completedReads} of {status.targetReads} style reads completed</h2><PilotProgress completed={status.completedReads} waiting={waiting} /><p className="text-[13px] leading-6 text-ink-2">A read counts once you have answered it. {waiting ? `${waiting} ${waiting === 1 ? "read is" : "reads are"} waiting for your answer. ` : ""}Collection ends after the first 10 answers or 14 days.</p></PilotCard>
      <section className="max-w-[820px] space-y-3"><h2 className="text-[16px] font-medium">Your answers so far</h2><div className="grid grid-cols-2 gap-3 sm:grid-cols-4">{counts.map((item) => <PilotCard key={item.label} className={item.label === "waiting" ? "border-accent-mid bg-accent-tint p-4" : "p-4"}><p className="capitalize text-ink-2">{item.label}</p><p className="mt-2 font-mono text-[24px]">{item.value}</p></PilotCard>)}</div><p className="text-[13px] text-ink-2">These are counts, not a score. Waiting reads are finished games that still need your answer. This pilot does not measure improvement as a player.</p></section>
      <PilotCard className="max-w-[820px] bg-panel p-5 text-[13px] leading-6 text-ink-2"><strong className="text-ink">What this shows.</strong> These answers tell the study whether Sarce&apos;s descriptions resonate with you. They do not grade your chess or measure improvement. Current state: <strong className="text-ink">{status.state}</strong>.</PilotCard>
      <Link href="/account" className="inline-flex min-h-11 items-center text-accent-text underline">Your data and taking part</Link>
    </main></PilotShell>
  );
}

export default function ProgressPage() {
  return <PilotModePage normal={<Progress />} pilot={<Progress />} />;
}
