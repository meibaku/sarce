"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { PilotShell } from "@/components/pilot/pilot-shell";
import { PilotButton, PilotCard, PilotMessage } from "@/components/pilot/pilot-ui";
import { usePilotStatus } from "@/components/pilot/pilot-status";
import { Board } from "@/components/ui/board";
import { getWhy, saveMoveIntent, type WhyApi } from "@/lib/api";

export function PilotEvidence({ gameId, ply }: { gameId: string; ply: number }) {
  const { status } = usePilotStatus();
  const [data, setData] = useState<WhyApi | null>(null);
  const [line, setLine] = useState(0);
  const [note, setNote] = useState("");
  const [savedNote, setSavedNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const draftKey = `sarce-pilot-note:${gameId}:${ply}`;

  useEffect(() => {
    getWhy(gameId, ply).then((result) => {
      setData(result);
      const draft = sessionStorage.getItem(draftKey);
      setNote(draft ?? result.privateNote ?? "");
      setSavedNote(result.privateNote ?? "");
    }).catch(() => setMessage("This evidence could not be loaded. The style read is still available."));
  }, [draftKey, gameId, ply]);

  useEffect(() => {
    if (note === savedNote) sessionStorage.removeItem(draftKey);
    else sessionStorage.setItem(draftKey, note);
  }, [draftKey, note, savedNote]);

  const continuation = data?.lines[0]?.steps ?? [];
  const fen = line === 0 ? data?.fenBefore : continuation[line - 1]?.fen;
  const criteria = useMemo(() => data?.brilliant.slice(0, 4) ?? [], [data]);
  const editable = status?.collectionActive ?? false;

  async function saveNote() {
    if (!editable) return;
    setSaving(true); setMessage(null);
    try {
      const result = await saveMoveIntent(gameId, ply, { type: null, note });
      if (result.note !== note) throw new Error("saved note did not match");
      setSavedNote(result.note);
    } catch { setMessage("The private note was not saved. Your draft remains here."); }
    finally { setSaving(false); }
  }

  if (!data || !fen) return <PilotShell><main className="mx-auto max-w-[1080px] px-5 py-8">{message ? <PilotMessage role="alert">{message}</PilotMessage> : <div className="pilot-skeleton h-[520px] rounded-[9px]" />}</main></PilotShell>;
  return (
    <PilotShell><main className="mx-auto max-w-[1080px] space-y-6 px-5 py-8">
      <div><Link href={`/games/${gameId}`} className="inline-flex min-h-11 items-center text-accent-text">← Style read</Link><div className="mt-3 flex items-baseline gap-4"><span className="rounded-full border border-[#b85700] px-3 py-2 font-mono text-[#9d4b08]">!!</span><h1 className="font-mono text-[28px]">{data.label}</h1></div></div>
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(320px,480px)_1fr]">
        <section className="space-y-4" aria-label="Review board"><Board fen={fen} orientation={data.orientation} label={`Review position for ${data.label}`} /><div className="flex gap-2"><button type="button" className="min-h-11 rounded-[7px] border border-line-2 px-4 disabled:opacity-40" disabled={line === 0} onClick={() => setLine((value) => Math.max(0, value - 1))}>‹ Prev</button><button type="button" className="min-h-11 rounded-[7px] border border-line-2 px-4 disabled:opacity-40" disabled={line >= continuation.length} onClick={() => setLine((value) => Math.min(continuation.length, value + 1))}>Next ›</button><span className="self-center font-mono text-[11px] text-muted">Review · {line}/{continuation.length}</span></div></section>
        <div className="space-y-4"><PilotCard className="border-ink p-5"><h2 className="text-[16px] font-medium">Why {data.label} counts as Brilliant</h2><p className="mt-1 text-[13px] text-muted">The four admitted criteria, using stored evidence.</p><ul className="mt-4 divide-y divide-line">{criteria.map((criterion) => <li key={criterion.rule} className="grid grid-cols-[20px_1fr] gap-2 py-4 text-[13px] leading-6"><span aria-label={criterion.passed ? "passes" : "does not pass"}>{criterion.passed ? "✓" : "·"}</span><span><strong>{criterion.rule}</strong><br /><span className="text-ink-2">{criterion.detail}</span></span></li>)}</ul><div className="mt-4 border-t border-line pt-4"><p className="text-[12px] font-medium">Soundness boundary <span className="font-normal text-muted">· expected points, from your side</span></p><div className="relative mt-5 h-2 bg-panel"><span className="absolute left-1/2 top-[-6px] h-5 border-l border-dashed border-[#b85700]" /><span className="absolute left-[60%] top-[-6px] h-5 border-l-2 border-ink" /></div><div className="mt-3 flex justify-between font-mono text-[11px] text-muted"><span>played {data.evalAfter ?? "?"}</span><span>limit 0.03 EP from best</span><span>best {data.best ?? "?"}</span></div></div></PilotCard>
          <details className="rounded-[9px] border border-line bg-panel p-4"><summary className="min-h-11 cursor-pointer content-center font-medium">Engine continuation <span className="font-normal text-muted">· supporting evidence</span></summary><p className="mt-3 font-mono text-[12px] leading-6">{continuation.map((step) => step.san).join(" ") || "No continuation is stored."}</p></details>
          <PilotCard className="p-5"><label htmlFor="private-note" className="font-medium">Private note</label><p className="mt-1 text-[12px] text-muted">Visible only in your account export and this game.</p><textarea id="private-note" value={note} disabled={!editable} onChange={(event) => setNote(event.target.value)} maxLength={2000} className="mt-3 min-h-28 w-full rounded-[7px] border border-line-2 bg-surface p-3" />{message && <div className="mt-3"><PilotMessage role="alert">{message}</PilotMessage></div>}<PilotButton type="button" className="mt-3" disabled={!editable || saving || note === savedNote} onClick={saveNote}>{saving ? "Saving…" : note === savedNote ? "Saved" : "Save private note"}</PilotButton></PilotCard>
        </div>
      </div>
    </main></PilotShell>
  );
}
