"use client";

import Link from "next/link";
import { PilotCard, PilotMessage } from "@/components/pilot/pilot-ui";
import { usePilotStatus } from "@/components/pilot/pilot-status";
import { SarceMark } from "@/components/ui/icons";

export default function PrivacyPage() {
  const { status } = usePilotStatus();
  return (
    <main data-pilot-shell className="min-h-dvh bg-page px-5 py-10 text-ink">
      <div className="mx-auto max-w-[760px] space-y-6">
        <div className="flex items-center gap-3"><SarceMark height={23} /><span className="text-[18px] font-medium">sarce</span><span className="font-mono text-[11px] text-muted">Style pilot privacy</span></div>
        <div><p className="font-mono text-[11px] text-muted">Version {status?.privacyVersion ?? "pending"}</p><h1 className="pilot-serif mt-2 text-[34px]">Pilot privacy summary</h1></div>
        <PilotMessage role="alert">This is the supplied participant summary, not a signed privacy notice. Admission stays closed until the full notice, protocol, retention period, and cross-border basis are approved.</PilotMessage>
        <PilotCard className="space-y-5 p-5 text-[14px] leading-6 text-ink-2">
          <section><h2 className="font-medium text-ink">What Sarce uses</h2><p>Your sign-in identity, connected chess username, finished games, analysis, private notes, and your Yes, Partly or No answers and comments.</p></section>
          <section><h2 className="font-medium text-ink">Why</h2><p>To test whether Sarce&apos;s post-game style reads, built around Brilliant moves, sound like the participant who played the game. This pilot does not measure chess improvement.</p></section>
          <section><h2 className="font-medium text-ink">Where and for how long</h2><p>The selected topology uses managed Supabase and persistent analysis hosting in Singapore. The approved cross-border basis and backup retention period must appear in the signed notice before admission opens. Current configured backup retention: {status?.backupRetentionDays ? `${status.backupRetentionDays} days` : "not approved"}.</p></section>
          <section><h2 className="font-medium text-ink">Your choices</h2><p>You may correct an answer or note during the collection window, withdraw, export your data, or delete your account. Existing reads, export, and deletion remain available after the pilot becomes read-only.</p></section>
        </PilotCard>
        <div className="flex gap-5"><Link href="/pilot" className="min-h-11 content-center text-accent-text underline">Back to admission</Link>{status?.admitted && <Link href="/account" className="min-h-11 content-center text-accent-text underline">Account and privacy controls</Link>}</div>
      </div>
    </main>
  );
}
