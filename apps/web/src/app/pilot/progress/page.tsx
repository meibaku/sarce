"use client";

import Link from "next/link";
import { PilotModePage, usePilotStatus } from "@/components/pilot/pilot-status";
import { PilotShell } from "@/components/pilot/pilot-shell";
import { PilotCard, PilotProgress } from "@/components/pilot/pilot-ui";

function Progress() {
  const { status } = usePilotStatus();
  if (!status) return null;
  const date = (value: string | null) => value ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value)) : "—";
  return (
    <PilotShell><main className="mx-auto max-w-[1080px] space-y-7 px-5 py-8">
      <div><p className="font-mono text-[11px] text-muted">{date(status.startsAt)} to {date(status.endsAt)}</p><h1 className="pilot-serif mt-2 text-[32px]">Pilot progress</h1></div>
      <PilotCard className="max-w-[820px] space-y-4 p-6"><h2 className="pilot-serif text-[24px]">{status.completedReads} of {status.targetReads} style reads completed</h2><PilotProgress completed={status.completedReads} /><p className="text-[13px] text-ink-2">A read counts once you have answered it. The collection ends after the first 10 answers or 14 days.</p></PilotCard>
      <section className="max-w-[820px] space-y-3"><h2 className="text-[16px] font-medium">Your answers so far</h2><div className="grid gap-3 sm:grid-cols-3">{(["yes", "partly", "no"] as const).map((answer) => <PilotCard key={answer} className="p-4"><p className="capitalize text-ink-2">{answer}</p><p className="mt-2 font-mono text-[24px]">{status.answers[answer]}</p></PilotCard>)}</div><p className="text-[13px] text-ink-2">These are counts, not a score. Every answer is equally useful; this pilot does not measure improvement as a player.</p></section>
      <PilotCard className="max-w-[820px] bg-panel p-5 text-[13px] leading-6 text-ink-2">Current state: <strong className="text-ink">{status.state}</strong>. Existing reads, export, and deletion remain available when collection is read-only.</PilotCard>
      <Link href="/account" className="inline-flex min-h-11 items-center text-accent-text underline">Your data and taking part</Link>
    </main></PilotShell>
  );
}

export default function ProgressPage() {
  return <PilotModePage normal={<Progress />} pilot={<Progress />} />;
}
