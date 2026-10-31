"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { PilotShell } from "@/components/pilot/pilot-shell";
import { PilotButton, PilotCard, PilotMessage } from "@/components/pilot/pilot-ui";
import { usePilotStatus } from "@/components/pilot/pilot-status";
import { getGameSummary, getPilotFeedback, getWhy, savePilotFeedback, type PilotFeedback } from "@/lib/api";
import { moveLabel } from "@/lib/format";
import type { FeltAnswer, SummaryApi } from "@/types/chess";

const OPTIONS: { value: FeltAnswer; label: string }[] = [
  { value: "yes", label: "Yes" }, { value: "partly", label: "Partly" }, { value: "no", label: "No" },
];

type BrilliantEvidence = { ply: number; checks: { rule: string; detail: string }[] };

export function PilotStyleRead({ gameId }: { gameId: string }) {
  const { status, refresh } = usePilotStatus();
  const [data, setData] = useState<SummaryApi | null>(null);
  const [evidence, setEvidence] = useState<BrilliantEvidence[]>([]);
  const [answer, setAnswer] = useState<FeltAnswer | null>(null);
  const [comment, setComment] = useState("");
  const [saved, setSaved] = useState<PilotFeedback | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const draftKey = `sarce-pilot-draft:${gameId}`;

  useEffect(() => {
    const draft = sessionStorage.getItem(draftKey);
    if (draft) {
      try { const parsed = JSON.parse(draft) as { answer: FeltAnswer | null; comment: string }; setAnswer(parsed.answer); setComment(parsed.comment); } catch { /* ignore a stale local draft */ }
    }
    Promise.all([getGameSummary(gameId), getPilotFeedback(gameId)]).then(async ([summary, feedback]) => {
      setData(summary);
      if (feedback) { setSaved(feedback); setAnswer(feedback.resonance); setComment(feedback.comment ?? ""); }
      const brilliant = summary.moments.filter((moment) => moment.glyph === "!!");
      const details = await Promise.all(brilliant.map(async (moment) => {
        const why = await getWhy(gameId, moment.ply);
        return { ply: moment.ply, checks: why.brilliant.slice(0, 4).filter((check) => check.passed) };
      }));
      setEvidence(details);
    }).catch(() => setMessage("This style read could not be loaded. Reference data remains unchanged."));
  }, [draftKey, gameId]);

  useEffect(() => {
    const matchesSaved = saved && saved.resonance === answer && (saved.comment ?? "") === comment;
    if (matchesSaved) sessionStorage.removeItem(draftKey);
    else {
      sessionStorage.setItem(draftKey, JSON.stringify({ answer, comment }));
      if (saved) setSaved(null);
    }
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

  if (!data) return <PilotShell><main className="mx-auto max-w-[1080px] px-5 py-8">{message ? <PilotMessage role="alert">{message}</PilotMessage> : <div className="pilot-skeleton h-72 rounded-[9px]" />}</main></PilotShell>;
  const brilliant = data.brilliant;
  const narrative = brilliant.count === 0 ? "No Brilliant moment appeared in this finished game. That is a neutral read, not a grade." : `The clearest style evidence appears in ${brilliant.count === 1 ? "one Brilliant moment" : `${brilliant.count} Brilliant moments`}.`;

  return (
    <PilotShell><main className="mx-auto max-w-[1080px] space-y-7 px-5 py-8">
      <div className="space-y-3"><Link href="/games" className="inline-flex min-h-11 items-center text-accent-text">← Games</Link><p className="font-mono text-[11px] text-muted">vs {data.opponent ?? "an opponent"} · {data.timeControl ?? "finished game"} · {data.userColor ?? "your side"}</p><h1 className="pilot-serif max-w-[880px] text-[30px] leading-tight">{narrative}</h1><p className="max-w-[760px] text-[15px] leading-7 text-ink-2">Across {data.moves} moves, Sarce looked for sound, chosen material offers. The engine supplies boundaries; it does not judge your identity.</p></div>
      <div className="grid items-start gap-5 md:grid-cols-[1fr_0.9fr]">
        <div className="space-y-4"><PilotCard className="p-5"><p className="font-mono text-[11px] uppercase text-muted">Brilliant this game</p>{brilliant.count ? <p className="mt-3 font-mono text-[28px] text-[#a94d00]">{brilliant.pct.toFixed(1)}% <span className="text-[11px] text-muted">{brilliant.count} in {brilliant.of} moves</span></p> : <p className="pilot-serif mt-3 text-[22px]">No Brilliant moves in this game</p>}<p className="mt-3 text-[13px] text-ink-2">One game swings a lot. The across-read figure belongs on Home.</p></PilotCard>
          {data.moments.filter((moment) => moment.glyph === "!!").map((moment) => { const checks = evidence.find((item) => item.ply === moment.ply)?.checks ?? []; return <PilotCard key={moment.ply} className="p-5"><h2 className="font-mono text-[16px]">!! &nbsp;{moveLabel(moment.ply, moment.san)}</h2><p className="mt-2 text-[13px] text-ink-2">{moment.line}</p><h3 className="mt-5 text-[13px] font-medium">Why it counts as Brilliant</h3><ul className="mt-3 space-y-3">{checks.map((check) => <li key={check.rule} className="grid grid-cols-[18px_1fr] gap-2 text-[13px] leading-5"><span aria-hidden="true">✓</span><span><strong>{check.rule}.</strong> {check.detail}</span></li>)}</ul><Link href={`/games/${gameId}/evidence?ply=${moment.ply}`} className="mt-5 inline-flex min-h-11 items-center text-accent-text underline">See the evidence for {moveLabel(moment.ply, moment.san)}</Link></PilotCard>; })}
        </div>
        <PilotCard className="sticky top-5 border-ink p-5"><fieldset disabled={!canEdit || saving} className="space-y-4"><legend className="pilot-serif text-[22px]">Did this style read feel like you?</legend><div className="grid grid-cols-3 gap-2" role="radiogroup">{OPTIONS.map((option) => <label key={option.value} className={`grid min-h-14 cursor-pointer place-items-center rounded-[7px] border font-medium ${answer === option.value ? "border-ink bg-panel" : "border-line-2"}`}><input type="radio" name="pilot-answer" value={option.value} checked={answer === option.value} onChange={() => setAnswer(option.value)} className="sr-only" />{option.label}</label>)}</div><label className="block text-[13px] font-medium" htmlFor="pilot-comment">What sounded right or wrong? <span className="font-normal text-muted">Optional</span></label><textarea id="pilot-comment" value={comment} maxLength={500} onChange={(event) => setComment(event.target.value)} className="min-h-28 w-full rounded-[7px] border border-line-2 bg-surface p-3" /><p className="text-right font-mono text-[11px] text-muted">{comment.length} / 500</p>{message && <PilotMessage role="alert">{message}</PilotMessage>}<PilotButton type="button" disabled={!answer || !canEdit || saving} onClick={submit}>{saving ? "Saving…" : saved ? "Saved" : "Save answer"}</PilotButton><p className="text-[12px] text-muted">Yes, Partly and No are equally useful.</p></fieldset></PilotCard>
      </div>
    </main></PilotShell>
  );
}
