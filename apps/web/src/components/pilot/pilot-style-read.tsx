"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { PilotShell } from "@/components/pilot/pilot-shell";
import { PilotButton, PilotCard, PilotMessage } from "@/components/pilot/pilot-ui";
import { usePilotStatus } from "@/components/pilot/pilot-status";
import { getPilotRead, savePilotFeedback, type PilotFeedback, type PilotRead } from "@/lib/api";
import type { FeltAnswer } from "@/types/chess";

const OPTIONS: { value: FeltAnswer; label: string }[] = [
  { value: "yes", label: "Yes" }, { value: "partly", label: "Partly" }, { value: "no", label: "No" },
];

export function PilotStyleRead({ gameId }: { gameId: string }) {
  const { status, refresh } = usePilotStatus();
  const [data, setData] = useState<PilotRead | null>(null);
  const [answer, setAnswer] = useState<FeltAnswer | null>(null);
  const [comment, setComment] = useState("");
  const [saved, setSaved] = useState<PilotFeedback | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const draftKey = `sarce-pilot-draft:${gameId}`;

  useEffect(() => {
    const draft = sessionStorage.getItem(draftKey);
    let localDraft: { answer: FeltAnswer | null; comment: string } | null = null;
    if (draft) {
      try { localDraft = JSON.parse(draft) as { answer: FeltAnswer | null; comment: string }; } catch { /* ignore a stale local draft */ }
    }
    getPilotRead(gameId).then((read) => {
      setData(read);
      setSaved(read.feedback);
      if (localDraft) { setAnswer(localDraft.answer); setComment(localDraft.comment); }
      else if (read.feedback) { setAnswer(read.feedback.resonance); setComment(read.feedback.comment ?? ""); }
    }).catch(() => setMessage("This style read could not be loaded. Reference data remains unchanged."));
  }, [draftKey, gameId]);

  useEffect(() => {
    const matchesSaved = Boolean(saved && saved.resonance === answer && (saved.comment ?? "") === comment);
    if (matchesSaved) sessionStorage.removeItem(draftKey);
    else sessionStorage.setItem(draftKey, JSON.stringify({ answer, comment }));
  }, [answer, comment, draftKey, saved]);

  const canEdit = useMemo(() => {
    if (!status || status.state === "withdrawn" || status.state === "expired") return false;
    if (status.collectionActive) return true;
    return Boolean(saved && status.state === "complete" && status.endsAt && Date.now() < new Date(status.endsAt).getTime());
  }, [saved, status]);

  async function submit() {
    if (!answer || !canEdit) return;
    const submitted = { answer, comment };
    setSaving(true); setMessage(null);
    try {
      const result = await savePilotFeedback(gameId, submitted.answer, submitted.comment);
      if (result.resonance !== submitted.answer || (result.comment ?? "") !== submitted.comment) throw new Error("saved values did not match");
      setSaved(result); sessionStorage.removeItem(draftKey); await refresh();
    } catch {
      setMessage("Your answer was not saved. The draft is still here; check your connection and retry.");
    } finally { setSaving(false); }
  }

  if (!data) return <PilotShell><main className="mx-auto max-w-[1120px] px-5 py-8">{message ? <PilotMessage role="alert">{message}</PilotMessage> : <div className="pilot-skeleton h-72 rounded-[8px]" />}</main></PilotShell>;
  const brilliant = data.brilliant;
  const isSaved = Boolean(saved && saved.resonance === answer && (saved.comment ?? "") === comment);
  const result = data.result === "win" ? "Won" : data.result === "loss" ? "Lost" : data.result === "draw" ? "Draw" : "Finished";

  return (
    <PilotShell><main className="mx-auto max-w-[1120px] space-y-7 px-5 py-8">
      <div className="space-y-3"><Link href="/games" className="inline-flex min-h-11 items-center text-accent-text">← Games</Link><p className="font-mono text-[12px] text-muted">{result} vs {data.opponent ?? "an opponent"} · {data.timeControl ?? "finished game"} · {data.userColor ?? "your side"}{data.playedAt ? ` · ${new Date(data.playedAt).toLocaleDateString()}` : ""}</p><h1 className="pilot-serif max-w-[880px] text-[30px] leading-tight">{data.headline}</h1><p className="max-w-[760px] text-[15px] leading-7 text-ink-2">{data.summary} The engine supplies boundaries; it does not judge your identity.</p></div>
      <div className="grid items-start gap-5 md:grid-cols-[1fr_0.9fr]">
        <div className="space-y-4"><PilotCard className="p-5"><p className="font-mono text-[11px] uppercase text-muted">Brilliant this game</p>{brilliant.count ? <p className="mt-3 font-mono text-[28px] text-[#a94d00]">{brilliant.pct.toFixed(1)}% <span className="text-[11px] text-muted">{brilliant.count} in {brilliant.of} moves</span></p> : <p className="pilot-serif mt-3 text-[22px]">No Brilliant moves in this game</p>}<p className="mt-3 text-[13px] text-ink-2">One game swings a lot. The across-read figure belongs on Home.</p></PilotCard>
          {data.moments.map((moment) => <PilotCard key={moment.ply} className="p-5"><div className="flex items-center gap-3"><span className="grid h-[30px] w-[30px] place-items-center rounded-full border-[1.5px] border-[#b4570f] text-[12px] font-semibold text-[#9a4a0c]">!!</span><h2 className="font-mono text-[16px] font-medium">{moment.label}</h2></div><p className="mt-3 text-[13px] text-ink-2">{moment.line}</p><h3 className="mt-5 text-[13px] font-medium">Why it counts as Brilliant</h3><ul className="mt-3 space-y-3">{moment.criteria.map((check) => <li key={check.rule} className="grid grid-cols-[18px_1fr] gap-2 text-[13px] leading-5"><span aria-hidden="true">✓</span><span><strong>{check.rule}.</strong> {check.detail}</span></li>)}</ul><Link href={`/games/${gameId}/evidence?ply=${moment.ply}`} className="mt-5 inline-flex min-h-11 items-center text-accent-text underline">See the evidence for {moment.label}</Link></PilotCard>)}
        </div>
        <PilotCard className="sticky top-5 border-[1.5px] border-ink p-5"><fieldset disabled={!canEdit || saving} className="space-y-4"><legend className="pilot-serif text-[22px]">Did this style read feel like you?</legend><div className="grid grid-cols-3 gap-2" role="radiogroup">{OPTIONS.map((option) => <label key={option.value} className={`grid min-h-14 cursor-pointer place-items-center rounded-[6px] border-[1.5px] font-medium ${answer === option.value ? "border-ink bg-panel" : "border-line-2"}`}><input type="radio" name="pilot-answer" value={option.value} checked={answer === option.value} onChange={() => setAnswer(option.value)} className="sr-only" />{option.label}</label>)}</div><label className="block text-[13px] font-medium" htmlFor="pilot-comment">What sounded right or wrong? <span className="font-normal text-muted">Optional</span></label><textarea id="pilot-comment" value={comment} maxLength={500} onChange={(event) => setComment(event.target.value)} className="min-h-28 w-full rounded-[6px] border-[1.5px] border-line-2 bg-surface p-3" /><p className="text-right font-mono text-[11px] text-muted">{comment.length} / 500</p>{message && <PilotMessage role="alert">{message}</PilotMessage>}<PilotButton type="button" disabled={!answer || !canEdit || saving || isSaved} onClick={submit}>{saving ? "Saving…" : isSaved ? "Saved" : "Save answer"}</PilotButton><p className="text-[12px] text-muted">Yes, Partly and No are equally useful.</p></fieldset></PilotCard>
      </div>
    </main></PilotShell>
  );
}
