"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/shell/app-shell";
import { Board } from "@/components/ui/board";
import { PrimaryButton } from "@/components/ui/buttons";
import { Card, SectionLabel } from "@/components/ui/card";
import {
  getLearningReviewMetrics,
  getNextLearningReview,
  recordLearningReview,
  type LearningReviewItem,
  type LearningReviewMetrics,
} from "@/lib/api";

const DECISIONS = ["approve", "reject", "unclear"] as const;
const pct = (value: number | null) => value === null ? "—" : `${(value * 100).toFixed(1)}%`;

export default function LearningReviewPage() {
  const [item, setItem] = useState<LearningReviewItem | null>(null);
  const [metrics, setMetrics] = useState<LearningReviewMetrics | null>(null);
  const [decision, setDecision] = useState<(typeof DECISIONS)[number] | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [next, report] = await Promise.all([getNextLearningReview(), getLearningReviewMetrics()]);
      setItem(next.item);
      setMetrics(report);
      setDecision(null);
      setNote("");
      setMessage(next.complete ? "No unreviewed held-out items remain for this reviewer." : null);
    } catch {
      setMessage("This workspace is available only to configured study reviewers.");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function submit() {
    if (!item || !decision) return;
    setBusy(true);
    try {
      await recordLearningReview(item.id, decision, note);
      await load();
    } catch {
      setMessage("The vote was not recorded. It is safe to try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell title="train">
      <Link href="/train/learning" className="font-mono text-[11px] text-muted hover:text-ink">← Learning Evidence</Link>
      <div className="grid gap-4 lg:grid-cols-[minmax(320px,1fr)_minmax(280px,420px)]">
        <Card lead className="gap-4">
          <SectionLabel>Independent held-out review</SectionLabel>
          {item ? <>
            <Board compact fen={item.positionFen} orientation={item.positionFen.split(" ")[1] === "b" ? "black" : "white"} label="Candidate piece-safety position" />
            <div className="grid grid-cols-2 gap-2 font-mono text-[11px] text-muted">
              <span>Proposed · {item.proposedLabel}</span><span>Family · {item.familyKey}</span>
              <span>Detector · v{item.detectorVersion}</span><span>Search · {item.analysisNodes.toLocaleString()} nodes</span>
            </div>
            <details className="text-[12px] text-ink-2">
              <summary className="cursor-pointer font-medium">Versioned target and verification</summary>
              <pre className="mt-2 overflow-auto whitespace-pre-wrap font-mono text-[10px]">{JSON.stringify({ target: item.target, verification: item.verification }, null, 2)}</pre>
            </details>
            <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label="Review decision">
              {DECISIONS.map((value) => <button key={value} type="button" role="radio" aria-checked={decision === value} onClick={() => setDecision(value)} className={`h-11 rounded-[6px] border-[1.5px] text-[12px] font-medium capitalize ${decision === value ? "border-accent bg-accent-tint text-accent-text" : "border-line-2 bg-surface"}`}>{value}</button>)}
            </div>
            <textarea value={note} onChange={(event) => setNote(event.target.value)} maxLength={500} placeholder="Optional adjudication note" className="min-h-20 rounded-[6px] border-[1.5px] border-line-2 bg-surface p-3 text-[12px]" />
            <PrimaryButton onClick={submit} disabled={busy || !decision}>{busy ? "Recording…" : "Record independent vote"}</PrimaryButton>
          </> : <p className="text-[13px] text-muted">{message ?? "Loading next candidate…"}</p>}
        </Card>
        <Card className="gap-3">
          <SectionLabel>Qualification gate</SectionLabel>
          {metrics ? <>
            <Metric label="Held out adjudicated" value={`${metrics.adjudicated} / ${metrics.gates.minimumHeldout}`} />
            <Metric label="Reviewed precision" value={`${pct(metrics.precision)} / ${(metrics.gates.precision * 100).toFixed(0)}%`} />
            <Metric label="Raw agreement" value={pct(metrics.rawAgreement)} />
            <Metric label="Cohen's kappa" value={metrics.cohenKappa === null ? "—" : `${metrics.cohenKappa.toFixed(2)} / ${metrics.gates.kappaTarget.toFixed(2)}`} />
            <p className="text-[12px] leading-[1.5] text-ink-2">
              {metrics.mandatoryHumanReviewCanEnd ? "The preregistered precision and agreement gates are met." : "Mandatory human review continues. No automatic-serving claim is available yet."}
            </p>
          </> : <p className="text-[12px] text-muted">Metrics unavailable.</p>}
        </Card>
      </div>
    </AppShell>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="flex items-baseline justify-between gap-3 border-b border-hair pb-2"><span className="text-[12px] text-muted">{label}</span><span className="font-mono text-[13px]">{value}</span></div>;
}
