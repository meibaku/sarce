"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PilotShell } from "@/components/pilot/pilot-shell";
import { PilotPageSkeleton } from "@/components/pilot/pilot-status";
import { PilotButton, PilotCard, PilotMessage } from "@/components/pilot/pilot-ui";
import { usePilotStatus } from "@/components/pilot/pilot-status";
import { deleteAccount, downloadAccountExport, getDeletionStatus, withdrawFromPilot } from "@/lib/api";

type Receipt = { id: string; receipt: string; status: string };
const RECEIPT_KEY = "sarce-deletion-receipt";

export default function AccountPage() {
  const { status, loading, error, refresh } = usePilotStatus();
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [confirmLeave, setConfirmLeave] = useState(false);
  const [typed, setTyped] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  useEffect(() => {
    const raw = localStorage.getItem(RECEIPT_KEY);
    if (!raw) return;
    try {
      const saved = JSON.parse(raw) as Receipt;
      setReceipt(saved);
      getDeletionStatus(saved.id, saved.receipt).then((result) => setReceipt({ ...saved, status: result.status })).catch(() => undefined);
    } catch { localStorage.removeItem(RECEIPT_KEY); }
  }, []);

  async function withdraw() {
    setWorking(true); setMessage(null);
    try { await withdrawFromPilot(); await refresh(); setMessage("Withdrawal is recorded. Existing reads, export, and deletion remain available."); }
    catch { setMessage("Withdrawal was not saved. Nothing changed; retry or contact the pilot operator."); }
    finally { setWorking(false); }
  }

  async function erase() {
    if (typed !== "DELETE") return;
    setWorking(true); setMessage(null);
    try {
      const result = await deleteAccount();
      localStorage.setItem(RECEIPT_KEY, JSON.stringify(result));
      setReceipt(result);
    } catch { setMessage("Deletion is incomplete. Keep this page open and contact the pilot operator before retrying."); }
    finally { setWorking(false); }
  }

  if (receipt?.status === "complete") {
    return <main data-pilot-shell className="grid min-h-dvh place-items-center bg-page px-5 text-ink"><div className="max-w-lg space-y-5 text-center"><h1 className="pilot-serif text-[32px]">Your account has been deleted</h1><p className="leading-6 text-ink-2">The durable deletion job is complete. Keep the opaque receipt below if you need the operator to verify it after sign-in data is gone.</p><PilotCard className="p-4 font-mono text-[11px] break-all">Job {receipt.id}<br />Receipt {receipt.receipt}</PilotCard><Link href="/login" className="inline-flex min-h-11 items-center text-accent-text underline">Return to sign in</Link></div></main>;
  }

  if (loading) return <PilotPageSkeleton />;
  if (!status && error) return <main data-pilot-shell className="grid min-h-dvh place-items-center bg-page px-5 text-ink" role="alert"><div className="max-w-md space-y-4 text-center"><h1 className="pilot-serif text-[30px]">Sarce could not open your account</h1><p className="leading-6 text-ink-2">Your data has not changed. Check your connection and retry. Reference {error}.</p><PilotButton onClick={() => void refresh()}>Retry</PilotButton></div></main>;
  if (!status) return <main data-pilot-shell className="grid min-h-dvh place-items-center bg-page px-5"><Link href="/login" className="text-accent-text underline">Sign in to open account controls</Link></main>;
  return (
    <PilotShell><main className="mx-auto max-w-[800px] space-y-6 px-5 py-8">
      <div><p className="font-mono text-[11px] text-muted">Protocol {status.consent?.protocol_version ?? status.protocolVersion} · Privacy {status.consent?.privacy_version ?? status.privacyVersion}</p><h1 className="pilot-serif mt-2 text-[32px]">Account and privacy</h1></div>
      {message && <PilotMessage role="alert">{message}</PilotMessage>}
      <PilotCard className="p-5"><h2 className="font-medium">What you agreed to</h2><p className="mt-2 font-mono text-[11px] text-muted">{status.consent?.consented_at ? `Joined ${new Date(status.consent.consented_at).toLocaleDateString()}` : "Consent record unavailable"} · 18+ confirmed</p><Link href="/privacy" className="mt-3 inline-flex min-h-11 items-center text-accent-text underline">Read the pilot privacy summary</Link></PilotCard>
      <PilotCard className="p-5"><h2 className="font-medium">Export all your data</h2><p className="mt-2 text-[13px] leading-6 text-ink-2">One JSON file with your games, style reads, answers, comments, private notes, and consent record.</p><PilotButton className="mt-4 !border-ink !bg-surface !text-ink" onClick={() => downloadAccountExport().catch(() => setMessage("Export failed. Your data is unchanged; retry."))}>Export my data</PilotButton></PilotCard>
      <PilotCard className="p-5"><h2 className="font-medium">Something wrong?</h2><p className="mt-2 text-[13px] leading-6 text-ink-2">Reply to your invitation email with what should be corrected. You can edit pilot answers and private notes on each game while collection is active. Corrections are confirmed by email.</p></PilotCard>
      <PilotCard className="p-5"><h2 className="font-medium">Leave the pilot</h2><p className="mt-2 text-[13px] leading-6 text-ink-2">Sarce stops importing new games and asking questions. Existing reads stay available unless you delete the account.</p>{status.state === "withdrawn" ? <p className="mt-4 font-medium">Withdrawal recorded.</p> : <><label className="mt-4 flex min-h-11 items-center gap-3 text-[13px]"><input type="checkbox" checked={confirmLeave} onChange={(event) => setConfirmLeave(event.target.checked)} className="h-5 w-5" />I understand the pilot becomes read-only.</label><PilotButton className="mt-3 !border-ink !bg-surface !text-ink" disabled={!confirmLeave || working} onClick={withdraw}>Leave the pilot</PilotButton></>}</PilotCard>
      <section className="rounded-[8px] border-[1.5px] border-[#bd3328] bg-surface p-5 sm:p-6"><div className="max-w-[620px]"><p className="font-mono text-[10px] uppercase tracking-[0.1em] text-[#a82820]">Permanent action</p><h2 className="pilot-serif mt-2 text-[22px] text-[#a82820]">Delete your account</h2><p className="mt-3 text-[13px] leading-6 text-ink-2">This removes your active account data. Existing games and style reads will no longer be available.</p><div className="mt-4 rounded-[6px] border border-[#e4bbb7] bg-[#fff8f6] p-3 text-[12px] leading-5 text-ink-2"><strong className="text-ink">Restore protection remains.</strong> Sarce keeps only the deletion instruction needed to prevent an approved backup restore from putting deleted data back into service.</div></div><div className="mt-6 border-t border-[#e4bbb7] pt-5"><label htmlFor="delete-confirm" className="block text-[13px] font-medium">Type <span className="font-mono">DELETE</span> to confirm</label><div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-center"><input id="delete-confirm" value={typed} onChange={(event) => setTyped(event.target.value)} className="min-h-11 w-full rounded-[6px] border border-[#bd3328] bg-surface px-3 font-mono sm:max-w-xs" /><button type="button" disabled={typed !== "DELETE" || working} onClick={erase} className="min-h-11 w-full rounded-[6px] bg-[#a82820] px-5 font-medium text-white disabled:opacity-40 sm:w-auto">Delete my account permanently</button></div><p className="mt-3 text-[11px] text-muted">You will receive an opaque deletion receipt when the job completes.</p></div></section>
    </main></PilotShell>
  );
}
