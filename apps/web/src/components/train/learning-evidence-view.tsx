"use client";

import { useCallback, useEffect, useState } from "react";
import { Board } from "@/components/ui/board";
import { PrimaryButton, TextButton } from "@/components/ui/buttons";
import { Card, SectionLabel } from "@/components/ui/card";
import {
  createLearningSession,
  enrolLearning,
  getLearningStatus,
  getNextLearningPresentation,
  submitLearningAttempt,
  withdrawLearning,
  type LearningPhase,
  type LearningPresentation,
  type LearningStatus,
} from "@/lib/api";

const PHASES: LearningPhase[] = ["baseline", "learning", "immediate", "day7", "day28"];
const PHASE_LABELS: Record<LearningPhase, string> = {
  baseline: "Baseline", learning: "Learning", immediate: "Immediate check",
  day7: "Day 7", day28: "Day 28",
};

type Receipt = Awaited<ReturnType<typeof submitLearningAttempt>>;

export function LearningEvidenceView() {
  const [status, setStatus] = useState<LearningStatus | null>(null);
  const [invite, setInvite] = useState("");
  const [adult, setAdult] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [phase, setPhase] = useState<LearningPhase | null>(null);
  const [item, setItem] = useState<LearningPresentation | null>(null);
  const [square, setSquare] = useState<string | null>(null);
  const [noDanger, setNoDanger] = useState(false);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [startedAt, setStartedAt] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setStatus(await getLearningStatus());
    } catch (error) {
      setMessage(String(error).includes("401") ? "Sign in before opening an invitation." : "Learning Evidence is unavailable right now.");
    }
  }, []);

  useEffect(() => {
    setInvite(new URLSearchParams(window.location.search).get("invite") ?? "");
    void refresh();
  }, [refresh]);

  async function loadNext(id: string) {
    const next = await getNextLearningPresentation(id);
    setItem(next.presentation);
    setSquare(null);
    setNoDanger(false);
    setConfidence(null);
    setReceipt(null);
    setStartedAt(Date.now());
    if (next.complete) {
      setSessionId(null);
      setMessage("This section is recorded. Return when the next study window opens.");
      await refresh();
    }
  }

  async function begin() {
    if (!status) return;
    setBusy(true);
    setMessage(null);
    try {
      const open = status.sessions.find((session) => !session.completedAt);
      const completed = new Set(status.sessions.filter((session) => session.completedAt).map((session) => session.phase));
      const nextPhase = open?.phase ?? PHASES.find((candidate) => !completed.has(candidate));
      if (!nextPhase) {
        setMessage("All scheduled sections are complete. Thank you for contributing evidence.");
        return;
      }
      const session = open ?? await createLearningSession(nextPhase);
      setSessionId(session.sessionId);
      setPhase(session.phase);
      await loadNext(session.sessionId);
    } catch (error) {
      const text = String(error);
      setMessage(text.includes("outside its protocol window") ? "The next delayed check is not due yet." : "This section cannot start yet.");
    } finally {
      setBusy(false);
    }
  }

  async function enrol() {
    if (!invite.trim() || !adult) return;
    setBusy(true);
    setMessage(null);
    try {
      await enrolLearning(invite.trim(), adult);
      await refresh();
      setInvite("");
    } catch {
      setMessage("That invitation cannot be used. Ask the study operator for a current link.");
    } finally {
      setBusy(false);
    }
  }

  async function answer() {
    if (!item || !sessionId || confidence === null || (!square && !noDanger)) return;
    setBusy(true);
    setMessage(null);
    try {
      const saved = await submitLearningAttempt(item.presentationToken, {
        clientAttemptId: crypto.randomUUID(),
        response: noDanger ? { noImmediateDanger: true } : { square: square! },
        confidence,
        latencyMs: Math.min(Date.now() - startedAt, 3_600_000),
      });
      setReceipt(saved);
    } catch {
      setMessage("Your answer was not acknowledged. It is safe to try saving it again.");
    } finally {
      setBusy(false);
    }
  }

  async function withdraw() {
    setBusy(true);
    try {
      await withdrawLearning();
      await refresh();
      setItem(null);
      setMessage("You are withdrawn. No new study sections will be offered.");
    } finally {
      setBusy(false);
    }
  }

  if (!status) return <p className="text-[13px] text-muted">{message ?? "Loading Learning Evidence…"}</p>;

  if (!status.enrolled) {
    return (
      <Card lead className="mx-auto max-w-xl gap-4">
        <SectionLabel>Invite and consent</SectionLabel>
        <h1 className="text-[22px] font-medium">Join the piece-safety study</h1>
        <p className="text-[13px] leading-[1.6] text-ink-2">
          This pilot asks whether unseen chess positions help us measure recognition over time. Participation is voluntary;
          you can withdraw at any point, and the study does not change your style profile.
        </p>
        <label className="flex flex-col gap-1 text-[12px] text-muted">
          Invitation token
          <input
            value={invite}
            onChange={(event) => setInvite(event.target.value)}
            className="h-11 rounded-[6px] border-[1.5px] border-line-2 bg-surface px-3 font-mono text-[13px] text-ink"
          />
        </label>
        <label className="flex items-start gap-3 text-[13px] leading-[1.5] text-ink-2">
          <input type="checkbox" checked={adult} onChange={(event) => setAdult(event.target.checked)} className="mt-1" />
          I am 18 or older, understand that this is a research pilot, and consent to the study records described above.
        </label>
        {message && <p className="text-[12px] text-muted" role="status">{message}</p>}
        <PrimaryButton onClick={enrol} disabled={busy || !adult || !invite.trim()} className="self-start">
          Accept invitation
        </PrimaryButton>
      </Card>
    );
  }

  if (status.enrollment?.withdrawn_at) {
    return <Card lead><h1 className="text-[20px] font-medium">Participation withdrawn</h1><p className="mt-2 text-[13px] text-ink-2">No new study sections will be offered.</p></Card>;
  }

  if (!item) {
    return (
      <Card lead className="gap-4">
        <SectionLabel>Learning Evidence</SectionLabel>
        <h1 className="text-[22px] font-medium">What can your opponent safely take right now?</h1>
        <p className="max-w-2xl text-[13px] leading-[1.6] text-ink-2">
          Each section uses unseen positions and stays separate from your style identity. Assessment schedules do not adapt
          to confidence or previous answers.
        </p>
        <div className="flex flex-wrap gap-2">
          {PHASES.map((name) => {
            const done = status.sessions.some((session) => session.phase === name && session.completedAt);
            return <span key={name} className="rounded-[4px] border border-line px-2 py-1 font-mono text-[10px] text-muted">{PHASE_LABELS[name]} · {done ? "recorded" : "waiting"}</span>;
          })}
        </div>
        {message && <p className="text-[12px] text-muted" role="status">{message}</p>}
        <div className="flex flex-wrap gap-3">
          <PrimaryButton onClick={begin} disabled={busy}>{busy ? "Opening…" : "Start or continue"}</PrimaryButton>
          <TextButton onClick={withdraw} disabled={busy}>Withdraw from study</TextButton>
        </div>
      </Card>
    );
  }

  const answerText = receipt?.feedback.target.noImmediateDanger
    ? "No immediate material danger"
    : `Square${(receipt?.feedback.target.squares?.length ?? 0) === 1 ? "" : "s"}: ${receipt?.feedback.target.squares?.join(", ") ?? "—"}`;

  return (
    <div className="grid gap-4 md:grid-cols-[minmax(280px,420px)_minmax(280px,1fr)]">
      <Card lead className="gap-3">
        <span className="font-mono text-[11px] text-muted">{phase ? PHASE_LABELS[phase] : "Study"} · item {item.ordinal}</span>
        <Board
          compact
          fen={item.positionFen}
          orientation={item.positionFen.split(" ")[1] === "b" ? "black" : "white"}
          label="Study position. Select the piece or square in immediate danger."
          onSquareClick={receipt ? undefined : (nextSquare) => { setSquare(nextSquare); setNoDanger(false); }}
          selected={square}
        />
      </Card>
      <Card className="gap-4">
        <SectionLabel>Unlabelled position</SectionLabel>
        <h1 className="text-[20px] font-medium">What can your opponent safely take right now?</h1>
        {!receipt ? (
          <>
            <p className="text-[13px] text-ink-2">Select a piece or square, or choose no immediate material danger.</p>
            <button
              type="button"
              onClick={() => { setNoDanger(true); setSquare(null); }}
              className={`h-11 rounded-[6px] border-[1.5px] text-[13px] font-medium ${noDanger ? "border-accent bg-accent-tint text-accent-text" : "border-line-2 bg-surface"}`}
            >
              No immediate material danger
            </button>
            <div className="flex flex-col gap-2">
              <span className="text-[13px] font-medium">How confident are you?</span>
              <div className="grid grid-cols-5 gap-2" role="radiogroup" aria-label="Confidence from 1 to 5">
                {[1, 2, 3, 4, 5].map((value) => (
                  <button
                    key={value}
                    type="button"
                    role="radio"
                    aria-checked={confidence === value}
                    onClick={() => setConfidence(value)}
                    className={`h-11 rounded-[6px] border-[1.5px] font-mono text-[13px] ${confidence === value ? "border-accent bg-accent-tint text-accent-text" : "border-line-2 bg-surface"}`}
                  >{value}</button>
                ))}
              </div>
            </div>
            {message && <p className="text-[12px] text-muted" role="status">{message}</p>}
            <PrimaryButton onClick={answer} disabled={busy || confidence === null || (!square && !noDanger)}>
              {busy ? "Recording…" : "Record answer"}
            </PrimaryButton>
          </>
        ) : (
          <div className="flex flex-col gap-3" role="status">
            <span className="font-mono text-[12px] text-accent-text">Recorded durably</span>
            <p className="text-[15px] font-medium">{receipt.correct ? "You identified the relation." : "Look once more at the material relation."}</p>
            <p className="text-[13px] text-ink-2">Answer: {answerText}</p>
            <PrimaryButton onClick={() => loadNext(sessionId!)}>Continue · {receipt.remaining} left</PrimaryButton>
          </div>
        )}
      </Card>
    </div>
  );
}
