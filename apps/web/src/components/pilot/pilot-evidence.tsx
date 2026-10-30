"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { PilotShell } from "@/components/pilot/pilot-shell";
import { PilotButton, PilotCard, PilotMessage } from "@/components/pilot/pilot-ui";
import { usePilotStatus } from "@/components/pilot/pilot-status";
import { Board, parseFen } from "@/components/ui/board";
import { getPilotRead, getWhy, saveMoveIntent, type PilotRead, type WhyApi } from "@/lib/api";

const CRITERIA = ["Material offered", "Sound", "Not already winning", "Not forced"];
const PIECE_GLYPHS: Record<string, string> = { P: "♙", N: "♘", B: "♗", R: "♖", Q: "♕", p: "♟", n: "♞", b: "♝", r: "♜", q: "♛" };
const STARTING_COUNTS: Record<string, number> = { P: 8, N: 2, B: 2, R: 2, Q: 1, p: 8, n: 2, b: 2, r: 2, q: 1 };

function moveArrow(uci?: string | null) {
  return uci && uci.length >= 4 ? { from: uci.slice(0, 2), to: uci.slice(2, 4) } : null;
}

function capturedPieces(fen: string) {
  const counts: Record<string, number> = {};
  Object.values(parseFen(fen)).forEach((piece) => { counts[piece] = (counts[piece] ?? 0) + 1; });
  const missing = (pieces: string[]) => pieces.flatMap((piece) => Array.from({ length: Math.max(0, STARTING_COUNTS[piece] - (counts[piece] ?? 0)) }, () => piece));
  return { whiteTook: missing(["p", "n", "b", "r", "q"]), blackTook: missing(["P", "N", "B", "R", "Q"]) };
}

function MaterialTray({ label, pieces }: { label: string; pieces: string[] }) {
  return <div className="flex min-h-7 items-center justify-between gap-3 text-[11px] text-muted"><span>{label}</span><span className="font-serif text-[19px] leading-none text-ink" aria-label={pieces.length ? `${pieces.length} captured pieces` : "No captured pieces"}>{pieces.length ? pieces.map((piece, index) => <span key={`${piece}-${index}`}>{PIECE_GLYPHS[piece]}</span>) : "—"}</span></div>;
}

export function PilotEvidence({ gameId, ply }: { gameId: string; ply: number }) {
  const { status } = usePilotStatus();
  const [data, setData] = useState<WhyApi | null>(null);
  const [read, setRead] = useState<PilotRead | null>(null);
  const [line, setLine] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [activeCriterion, setActiveCriterion] = useState<number | null>(null);
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
    getPilotRead(gameId).then(setRead).catch(() => undefined);
  }, [draftKey, gameId, ply]);

  useEffect(() => {
    if (note === savedNote) sessionStorage.removeItem(draftKey);
    else sessionStorage.setItem(draftKey, note);
  }, [draftKey, note, savedNote]);

  const continuation = data?.lines[0]?.steps ?? [];
  const currentStep = line > 0 ? continuation[line - 1] : null;
  const fen = currentStep?.fen ?? data?.fenBefore;
  const currentArrow = moveArrow(currentStep?.uci ?? data?.playedUci);
  const criteria = useMemo(() => data?.brilliant.slice(0, 4) ?? [], [data]);
  const orientation = data ? (flipped ? (data.orientation === "white" ? "black" : "white") : data.orientation) : "white";
  const captures = fen ? capturedPieces(fen) : { whiteTook: [], blackTook: [] };
  const userTook = data?.orientation === "black" ? captures.blackTook : captures.whiteTook;
  const opponentTook = data?.orientation === "black" ? captures.whiteTook : captures.blackTook;
  const hot = activeCriterion == null || !currentArrow ? currentArrow ? [currentArrow.from, currentArrow.to] : [] : activeCriterion < 2 ? [currentArrow.from, currentArrow.to] : activeCriterion === 2 ? [currentArrow.to] : [currentArrow.from];
  const liveCaption = activeCriterion == null ? `${data?.label ?? "The played move"} is highlighted on the board.` : `${CRITERIA[activeCriterion]}: ${criteria[activeCriterion]?.detail ?? "Evidence unavailable."}`;
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

  if (!data || !fen) return <PilotShell><main className="mx-auto max-w-[1120px] px-5 py-8">{message ? <PilotMessage role="alert">{message}</PilotMessage> : <div className="pilot-skeleton h-[520px] rounded-[8px]" />}</main></PilotShell>;
  const resultLabel = read?.result ? read.result[0].toUpperCase() + read.result.slice(1) : "Finished game";
  const epGap = data.bestEp != null && data.playedEp != null ? Math.max(0, data.bestEp - data.playedEp) : null;
  const insideBoundary = data.playedEp != null && data.minimumEp != null ? data.playedEp >= data.minimumEp : null;
  return (
    <PilotShell><main className="mx-auto max-w-[1120px] space-y-6 px-5 py-8">
      <div><Link href={`/games/${gameId}`} className="inline-flex min-h-11 items-center text-accent-text">← Style read</Link><div className="mt-3 flex items-center gap-3"><span className="pilot-brilliant-mark grid h-9 w-9 shrink-0 place-items-center rounded-full border-[1.5px] border-[#b85700] font-mono text-[11px] text-[#9d4b08]">!!</span><div><p className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted">Brilliant evidence</p><h1 className="mt-1 font-mono text-[clamp(23px,4vw,28px)]">{data.label}</h1><p className="mt-1 text-[12px] text-muted">{resultLabel}{read?.opponent ? ` against ${read.opponent}` : ""} · move {Math.floor(ply / 2) + 1}{read?.moves ? ` of ${read.moves}` : ""}{read?.timeControl ? ` · ${read.timeControl}` : ""}</p></div></div></div>
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(320px,500px)_1fr]">
        <section className="space-y-3" aria-label="Review board">
          <PilotCard className="p-3"><MaterialTray label={`${read?.opponent ?? "Opponent"} has taken`} pieces={opponentTook} /><Board fen={fen} orientation={orientation} hot={hot} selected={currentArrow?.to} arrow={currentArrow} coordinates="inside" pieceStyle="glyphs" label={`Review position for ${data.label}`} /><MaterialTray label="You have taken" pieces={userTook} /></PilotCard>
          <div className="flex flex-wrap gap-2"><button type="button" className="min-h-11 rounded-[6px] border border-line-2 px-4 disabled:opacity-40" disabled={line === 0} onClick={() => setLine((value) => Math.max(0, value - 1))}>‹ Prev</button><button type="button" className="min-h-11 rounded-[6px] border border-line-2 px-4 disabled:opacity-40" disabled={line >= continuation.length} onClick={() => setLine((value) => Math.min(continuation.length, value + 1))}>Next ›</button><button type="button" className="min-h-11 rounded-[6px] border border-line-2 px-4" onClick={() => setFlipped((value) => !value)}>Flip board</button><span className="self-center font-mono text-[11px] text-muted">Review · {line}/{continuation.length}</span></div>
          <div className="flex gap-1 overflow-x-auto pb-1" aria-label="Continuation moves"><button type="button" onClick={() => setLine(0)} className={`min-h-11 shrink-0 rounded-[6px] border px-3 font-mono text-[11px] ${line === 0 ? "border-ink bg-ink text-surface" : "border-line-2"}`}>Position</button>{continuation.map((step, index) => <button type="button" key={`${step.uci}-${index}`} onClick={() => setLine(index + 1)} className={`min-h-11 shrink-0 rounded-[6px] border px-3 font-mono text-[11px] ${line === index + 1 ? "border-ink bg-ink text-surface" : "border-line-2"}`}>{step.san}</button>)}</div>
          <p className="sr-only" aria-live="polite">{liveCaption}</p>
        </section>
        <div className="space-y-4"><PilotCard className="border-[1.5px] border-ink p-5"><header className="border-b border-line pb-4"><p className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted">Four admitted criteria</p><h2 className="pilot-serif mt-2 text-[22px] leading-tight">Why this move counts as Brilliant</h2><p className="mt-2 max-w-[46ch] text-[13px] leading-5 text-ink-2">Focus a criterion to connect its explanation to the board. Engine values are supporting evidence, never a grade.</p></header><ul className="divide-y divide-line">{criteria.map((criterion, index) => <li key={criterion.rule} tabIndex={0} onFocus={() => setActiveCriterion(index)} onBlur={() => setActiveCriterion(null)} onMouseEnter={() => setActiveCriterion(index)} onMouseLeave={() => setActiveCriterion(null)} className="grid grid-cols-[28px_1fr] gap-3 rounded-[6px] py-4 text-[13px] leading-5 focus:bg-accent-tint focus:outline-none"><span aria-label={criterion.passed ? "passes" : "does not pass"} className="mt-0.5 grid h-5 w-5 place-items-center rounded-full border border-line-3 font-mono text-[10px]">{criterion.passed ? "✓" : "·"}</span><span><strong className="block text-[14px]">{CRITERIA[index]}</strong><span className="mt-1 block text-ink-2">{criterion.detail}</span></span></li>)}</ul><section className="mt-2 rounded-[6px] bg-panel p-4" aria-label="Soundness comparison"><div className="flex flex-wrap items-center justify-between gap-2"><div><p className="font-medium">Soundness check</p><p className="mt-1 text-[11px] text-muted">Expected points from your side</p></div><span className="rounded-full border border-[#b4570f] bg-surface px-3 py-1 text-[11px] font-medium text-[#8f460d]">{insideBoundary == null ? "Boundary unavailable" : insideBoundary ? "Inside the boundary" : "Outside the boundary"}</span></div><div className="mt-4 grid grid-cols-3 divide-x divide-line text-center"><div><span className="block font-mono text-[16px]">{data.playedEp?.toFixed(3) ?? "?"}</span><span className="mt-1 block text-[10px] uppercase tracking-[0.08em] text-muted">Played</span></div><div><span className="block font-mono text-[16px]">{data.minimumEp?.toFixed(3) ?? "?"}</span><span className="mt-1 block text-[10px] uppercase tracking-[0.08em] text-muted">Minimum</span></div><div><span className="block font-mono text-[16px]">{data.bestEp?.toFixed(3) ?? "?"}</span><span className="mt-1 block text-[10px] uppercase tracking-[0.08em] text-muted">Best · {data.bestMove ?? "—"}</span></div></div><p className="mt-4 border-t border-line pt-3 text-[12px] leading-5 text-ink-2">{epGap == null ? "The stored values do not support a numerical comparison." : `The played move was ${epGap.toFixed(3)} expected points from best; Brilliant allows at most 0.030.`}</p></section></PilotCard>
          <details className="rounded-[8px] border border-line bg-panel p-4"><summary className="min-h-11 cursor-pointer content-center font-medium">Engine continuation <span className="font-normal text-muted">· supporting evidence</span></summary><p className="mt-3 font-mono text-[12px] leading-6">{continuation.map((step) => step.san).join(" ") || "No continuation is stored."}</p></details>
          <PilotCard className="p-5"><label htmlFor="private-note" className="font-medium">Private note</label><p className="mt-1 text-[12px] text-muted">Visible only in your account export and this game.</p><textarea id="private-note" value={note} disabled={!editable} onChange={(event) => setNote(event.target.value)} maxLength={2000} className="mt-3 min-h-28 w-full rounded-[6px] border border-line-2 bg-surface p-3" />{message && <div className="mt-3"><PilotMessage role="alert">{message}</PilotMessage></div>}<PilotButton type="button" className="mt-3" disabled={!editable || saving || note === savedNote} onClick={saveNote}>{saving ? "Saving…" : note === savedNote ? "Saved" : "Save private note"}</PilotButton></PilotCard>
        </div>
      </div>
    </main></PilotShell>
  );
}
