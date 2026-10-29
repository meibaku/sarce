"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { PilotButton, PilotCard, PilotMessage } from "@/components/pilot/pilot-ui";
import { PilotPageSkeleton, usePilotStatus } from "@/components/pilot/pilot-status";
import { SarceMark } from "@/components/ui/icons";
import { consentToPilot, redeemPilotInvitation } from "@/lib/api";

export default function PilotPage() {
  const router = useRouter();
  const { status, loading, error, refresh } = usePilotStatus();
  const [code, setCode] = useState("");
  const [adult, setAdult] = useState(false);
  const [notice, setNotice] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && status?.admitted) router.replace("/");
  }, [loading, router, status?.admitted]);

  if (loading) return <PilotPageSkeleton />;
  if (!status) {
    return (
      <main data-pilot-shell className="grid min-h-dvh place-items-center bg-page px-5 text-ink">
        <div className="max-w-md space-y-4 text-center">
          <h1 className="pilot-serif text-[30px]">Sign in to open your invitation</h1>
          <p className="text-ink-2">Use the email address that received the pilot invitation.</p>
          {error && <PilotMessage role="alert">Status reference {error}</PilotMessage>}
          <Link href="/login" className="inline-flex min-h-11 items-center rounded-[7px] bg-ink px-5 font-medium text-surface">Sign in</Link>
        </div>
      </main>
    );
  }

  const versionsReady = Boolean(status.protocolVersion && status.privacyVersion && status.backupRetentionDays);
  const canJoin = status.admissionOpen && versionsReady && adult && notice && (status.invitationRedeemed || code.trim().length >= 24);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!canJoin || !status?.protocolVersion || !status.privacyVersion) return;
    setSubmitting(true);
    setMessage(null);
    try {
      if (!status.invitationRedeemed) await redeemPilotInvitation(code.trim());
      await consentToPilot(status.protocolVersion, status.privacyVersion);
      await refresh();
      router.replace("/");
    } catch (cause) {
      const detail = cause instanceof Error ? cause.message : "unknown";
      if (detail.toLowerCase().includes("expired")) setMessage("This invitation has expired. Ask the pilot operator for a new one.");
      else if (status.invitationRedeemed) setMessage("Your invitation is safe, but consent was not saved. Review the boxes and try again.");
      else setMessage("That invitation is invalid, expired, or already used.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main data-pilot-shell className="min-h-dvh bg-page px-5 py-10 text-ink md:py-12">
      <div className="mx-auto max-w-[640px] space-y-7">
        <div className="flex items-center gap-3"><SarceMark height={24} /><span className="text-[18px] font-medium">sarce</span><span className="rounded-full border border-line-2 px-2 py-1 font-mono text-[11px]">Style pilot · by invitation</span></div>
        <div className="space-y-3">
          <h1 className="pilot-serif text-[34px] leading-[1.18]">Does Sarce read your games the way you would describe them?</h1>
          <p className="max-w-[620px] text-[15px] leading-7 text-ink-2">For two weeks, Sarce reads your finished games and writes a short note on the style it sees, built around Brilliant moves. After each note you tell us whether it sounded like you. That is the whole pilot.</p>
        </div>
        <div className="grid overflow-hidden rounded-[9px] border border-line bg-surface sm:grid-cols-3">
          {[["How long", "Two weeks, or your first 10 style reads"], ["What you do", "Answer Yes, Partly or No after each read"], ["What is read", "Finished games only, never live ones"]].map(([label, text]) => <div key={label} className="border-b border-line p-4 last:border-0 sm:border-r sm:border-b-0"><p className="font-mono text-[11px] text-muted">{label}</p><p className="mt-1 text-[13px] leading-5">{text}</p></div>)}
        </div>
        <PilotCard className="p-5">
          <form className="space-y-5" onSubmit={submit}>
            <div><label htmlFor="invitation" className="mb-2 block text-[13px] font-medium">Invitation code</label><input id="invitation" value={code} onChange={(event) => setCode(event.target.value)} disabled={status.invitationRedeemed} placeholder={status.invitationRedeemed ? "Invitation redeemed" : "SARCE-…"} autoComplete="one-time-code" className="min-h-11 w-full max-w-xs rounded-[6px] border border-line-2 bg-surface px-3 font-mono disabled:bg-panel" /></div>
            <label className="flex min-h-11 items-start gap-3 text-[13px]"><input type="checkbox" checked={adult} onChange={(event) => setAdult(event.target.checked)} className="mt-1 h-5 w-5" /><span>I am 18 or older.</span></label>
            <label className="flex min-h-11 items-start gap-3 text-[13px]"><input type="checkbox" checked={notice} onChange={(event) => setNotice(event.target.checked)} className="mt-1 h-5 w-5" /><span>I have read the <Link href="/privacy" className="text-accent-text underline">pilot privacy summary</Link> and agree to take part under the named protocol.</span></label>
            {!status.admissionOpen && <PilotMessage role="alert">Admission is not open. The signed protocol, privacy notice, retention period, cross-border basis, and release evidence are still pending.</PilotMessage>}
            {message && <PilotMessage role="alert">{message}</PilotMessage>}
            <div className="flex flex-wrap items-center gap-5"><PilotButton disabled={!canJoin || submitting}>{submitting ? "Saving…" : "Join the pilot"}</PilotButton><Link href="/privacy" className="min-h-11 content-center text-[13px] text-accent-text underline">Read the privacy summary</Link></div>
            <p className="font-mono text-[11px] text-muted">Protocol {status.protocolVersion ?? "pending"} · Privacy notice {status.privacyVersion ?? "pending"} · Backup retention {status.backupRetentionDays ? `${status.backupRetentionDays} days` : "pending"}</p>
          </form>
        </PilotCard>
      </div>
    </main>
  );
}
