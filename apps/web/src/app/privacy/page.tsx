"use client";

import Link from "next/link";
import { useState } from "react";
import { AppShell } from "@/components/shell/app-shell";
import { deleteAccount, downloadAccountExport, withdrawFromPilot } from "@/lib/api";

export default function PrivacyPage() {
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  return <AppShell title="privacy"><h1 className="text-[22px] font-medium">Pilot privacy</h1>
    <section className="space-y-3 rounded-[8px] border border-line bg-surface p-[18px] text-[13px] leading-[1.6] text-ink-2">
      <p>Sarce stores your sign-in identity, connected chess usernames, completed games, analysis, notes and pilot answers. The purpose is to test whether the Brilliant style read resonates with you.</p>
      <p>Supabase stores Auth and PostgreSQL data in Singapore, the persistent analysis server runs at Hetzner Singapore, and Vercel delivers the web interface. Anthropic receives nothing in this pilot because AI video help is disabled.</p>
      <p>Only the pilot operator can access participant-level operations. Pilot reports use participant-first aggregates. Backups expire under the documented retention schedule; deleted data may remain in encrypted backups until expiry and is not restored into active service.</p>
      <p>Participation is voluntary. You may withdraw, export your data, request correction, or delete the account.</p>
    </section>
    <div className="flex flex-wrap gap-3"><button onClick={() => downloadAccountExport().catch(() => setMessage("Export failed. Try again."))} className="h-10 rounded-[6px] border-[1.5px] border-ink px-4 text-[13px] font-medium">Export all my data</button><button onClick={() => withdrawFromPilot().then(() => setMessage("Withdrawn. Export and deletion remain available.")).catch(() => setMessage("Withdrawal failed."))} className="h-10 rounded-[6px] border-[1.5px] border-ink px-4 text-[13px] font-medium">Withdraw</button></div>
    <section className="space-y-2 rounded-[8px] border border-line p-[18px]"><h2 className="text-[16px] font-medium">Delete account permanently</h2><p className="text-[12px] text-muted">Type DELETE. This removes active account data and cannot be undone.</p><input value={confirm} onChange={(e) => setConfirm(e.target.value)} className="h-10 rounded-[6px] border-[1.5px] border-line-2 px-3" aria-label="Type DELETE to confirm" /><button disabled={confirm !== "DELETE"} onClick={() => deleteAccount().then((r) => { setMessage(`Deletion complete. Receipt ${r.id}`); }).catch(() => setMessage("Deletion is incomplete. Sign in and retry or contact the pilot operator."))} className="h-10 rounded-[6px] bg-ink px-4 text-[13px] font-medium text-white disabled:opacity-40">Delete my account</button></section>
    {message && <p className="text-[13px] text-ink-2">{message}</p>}<Link href="/pilot" className="text-[13px] text-accent-text">Back to pilot status</Link>
  </AppShell>;
}
