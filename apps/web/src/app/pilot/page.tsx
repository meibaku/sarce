"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { SarceMark } from "@/components/ui/icons";
import { consentToPilot, getPilotStatus, redeemPilotInvitation, type PilotStatus } from "@/lib/api";

export default function PilotPage() {
  const [status, setStatus] = useState<PilotStatus | null>(null);
  const [token, setToken] = useState("");
  const [adult, setAdult] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const load = () => getPilotStatus().then(setStatus).catch(() => setMessage("Sign in with the invited email address first."));
  useEffect(() => {
    void load();
  }, []);

  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col justify-center gap-4 px-6 py-12 text-ink">
      <SarceMark height={30} />
      <div><p className="font-mono text-[11px] text-accent-text">invite-only · adults · two weeks</p><h1 className="text-[24px] font-medium">Sarce style pilot</h1></div>
      <p className="text-[14px] leading-[1.6] text-ink-2">This pilot asks whether Sarce&apos;s post-game Brilliant read sounds like you. Experimental lenses are unavailable. You can withdraw, export or delete your data at any time.</p>
      {message && <p className="rounded-[6px] bg-panel p-3 text-[13px]">{message}</p>}
      {!status ? <Link href="/login" className="text-[13px] font-medium text-accent-text">Sign in →</Link> : status.admitted ? (
        <div className="space-y-3"><p className="text-[14px]">You&apos;re admitted. {status.completedReads} style reads completed.</p><Link href="/" className="inline-flex h-11 items-center rounded-[6px] bg-accent px-5 text-[14px] font-medium text-white">Open Sarce</Link></div>
      ) : !status.invitationRedeemed ? (
        <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); setMessage(null); redeemPilotInvitation(token.trim()).then(load).catch(() => setMessage("That invitation is invalid, expired or already used.")); }}>
          <label className="block text-[13px] font-medium" htmlFor="invite">Invitation code</label>
          <input id="invite" value={token} onChange={(e) => setToken(e.target.value)} required className="h-11 w-full rounded-[6px] border-[1.5px] border-line-2 px-3" />
          <button className="h-11 rounded-[6px] bg-accent px-5 text-[14px] font-medium text-white">Redeem invitation</button>
        </form>
      ) : (
        <div className="space-y-4 rounded-[8px] border border-line bg-surface p-[18px]">
          <h2 className="text-[17px] font-medium">Consent</h2>
          <p className="text-[13px] leading-[1.55] text-ink-2">Sarce stores your account, imported finished games, analyses and pilot answers in Singapore. Participation is voluntary. Results are reported as a small pilot signal, not proof of improvement.</p>
          <label className="flex items-start gap-3 text-[13px]"><input type="checkbox" className="mt-1" checked={adult} onChange={(e) => setAdult(e.target.checked)} /><span>I am at least 18, have read the <Link className="text-accent-text underline" href="/privacy">pilot privacy notice</Link>, and consent to protocol {status.protocolVersion} and privacy notice {status.privacyVersion}.</span></label>
          <button disabled={!adult} onClick={() => status.protocolVersion && status.privacyVersion && consentToPilot(status.protocolVersion, status.privacyVersion).then(setStatus).catch(() => setMessage("Consent could not be saved."))} className="h-11 rounded-[6px] bg-accent px-5 text-[14px] font-medium text-white disabled:opacity-40">Join the pilot</button>
        </div>
      )}
      <Link href="/privacy" className="text-[13px] text-accent-text">Privacy, export and deletion</Link>
    </main>
  );
}
