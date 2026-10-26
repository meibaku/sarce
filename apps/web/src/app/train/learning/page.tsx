"use client";

import Link from "next/link";
import { AppShell } from "@/components/shell/app-shell";
import { LearningEvidenceView } from "@/components/train/learning-evidence-view";

export default function LearningEvidencePage() {
  return (
    <AppShell title="train">
      <Link href="/train" className="font-mono text-[11px] text-muted hover:text-ink">← Back to Train</Link>
      <LearningEvidenceView />
    </AppShell>
  );
}
