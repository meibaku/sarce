"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { PrimaryButton, TextButton } from "@/components/ui/buttons";
import { Mascot } from "@/components/ui/mascot";
import { MoveBadge } from "@/components/ui/move-badge";
import { getHome, importChessComGames, importLichessGames, updateSettings } from "@/lib/api";
import { moveLabel } from "@/lib/format";
import type { HomeMoment } from "@/types/chess";

/*
 * Onboarding (handoff screen 1, max width 520): 1 connect (username only, no password) →
 * 2 a real moment from the last game, before any setup → 3 the style goal → 4 the one-question
 * rule and where the data lives.
 */

const GOALS: { id: string; title: string; detail: string; lo: number; hi: number }[] = [
  { id: "tal", title: "More Tal", detail: "Sacrifices and initiative · band 6–10%", lo: 6, hi: 10 },
  { id: "solid", title: "More solid", detail: "Safer replies, fewer risks · band 2–4%", lo: 2, hi: 4 },
  { id: "none", title: "No goal yet", detail: "Sarce just mirrors your games for now", lo: 0, hi: 15 },
];

const STEPS = ["Connect", "First moment", "Style goal", "One question"];

export function OnboardingFlow() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [site, setSite] = useState<"chess_com" | "lichess">("chess_com");
  const [username, setUsername] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [moment, setMoment] = useState<(HomeMoment & { opponent: string | null }) | null>(null);
  const [goal, setGoal] = useState("tal");

  useEffect(() => {
    if (step !== 1) return;
    getHome()
      .then((h) => {
        const m = h.latest?.moments[0];
        setMoment(m ? { ...m, opponent: h.latest?.opponent ?? null } : null);
      })
      .catch(() => setMoment(null));
  }, [step]);

  async function next() {
    if (step === 0) {
      const name = username.trim();
      if (!name) {
        setStatus("Enter your username first.");
        return;
      }
      setBusy(true);
      setStatus(null);
      try {
        const res = site === "lichess" ? await importLichessGames(name, true) : await importChessComGames(name, true);
        // Saved so new games keep arriving by themselves (automatic sync).
        await updateSettings(site === "lichess" ? { lichessUsername: name } : { chessComUsername: name }).catch(() => undefined);
        setStatus(res.message);
        setStep(1);
      } catch (err) {
        setStatus(err instanceof Error ? err.message : "That username couldn't be imported.");
      } finally {
        setBusy(false);
      }
      return;
    }
    if (step === 2) {
      const g = GOALS.find((x) => x.id === goal) ?? GOALS[0];
      await updateSettings({ goalLo: g.lo, goalHi: g.hi, sources: site }).catch(() => undefined);
    }
    if (step === 3) {
      router.push("/");
      return;
    }
    setStep(step + 1);
  }

  return (
    <div className="mx-auto flex w-full max-w-[520px] flex-col gap-4">
      {/* The handoff's inline mark leaves a descender gap below it; pb-1 keeps the same rhythm. */}
      <span className="self-start pb-1 text-ink">
        <Mascot state={["hello", "curious", "think", "proud"][step]} size={64} />
      </span>
      <div className="flex gap-[6px]" aria-hidden="true">
        {STEPS.map((s, i) => (
          <span key={s} className="h-[3px] flex-1 rounded-[2px]" style={{ background: i <= step ? "var(--ink)" : "var(--line)" }} />
        ))}
      </div>
      <span className="font-mono text-[11px] text-muted">
        Step {step + 1} of 4 · {STEPS[step]}
      </span>

      {step === 0 && (
        <>
          <h1 className="text-[26px] leading-[1.2] font-medium">Connect where you play</h1>
          <span className="text-[14px] leading-[1.55] text-muted">Username only, no password. Sarce reads finished games, never live ones.</span>
          <div className="flex flex-col gap-2">
            {(
              [
                ["chess_com", "Chess.com"],
                ["lichess", "Lichess"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                aria-pressed={site === id}
                onClick={() => setSite(id)}
                className={`flex h-11 items-center rounded-[6px] border-[1.5px] px-[14px] text-[13px] font-medium ${
                  site === id ? "border-accent bg-accent-tint text-accent-text" : "border-line-2 bg-surface text-ink"
                }`}
              >
                {label}
              </button>
            ))}
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder={site === "lichess" ? "your Lichess username" : "your Chess.com username"}
              aria-label="Username"
              autoComplete="username"
              className="h-11 rounded-[6px] border-[1.5px] border-line-2 bg-surface px-[14px] text-[13px] placeholder:text-faint"
              onKeyDown={(e) => e.key === "Enter" && next()}
            />
          </div>
        </>
      )}

      {step === 1 && (
        <>
          <h1 className="text-[26px] leading-[1.2] font-medium">Here&apos;s a moment from your last game</h1>
          <span className="text-[14px] leading-[1.55] text-muted">Value before setup: this is what Sarce does, before it asks you anything.</span>
          {moment ? (
            <div className="flex items-center gap-3 rounded-[8px] border-[1.5px] border-ink bg-surface p-[14px]">
              <MoveBadge glyph={moment.glyph} size={28} />
              <span className="flex flex-col gap-[2px]">
                <span className="font-mono text-[14px] font-medium">
                  {moveLabel(moment.ply, moment.san)} vs {moment.opponent ?? "your opponent"}
                </span>
                <span className="text-[13px] text-ink-2">{moment.line}</span>
              </span>
            </div>
          ) : (
            <div className="rounded-[8px] border-[1.5px] border-dashed border-line-3 p-[14px] text-[13px] text-ink-2">
              Your games are being read. The first moments appear on Home as soon as they&apos;re scored.
            </div>
          )}
          <span className="font-mono text-[11px] text-muted">More moments still being scored…</span>
        </>
      )}

      {step === 2 && (
        <>
          <h1 className="text-[26px] leading-[1.2] font-medium">Who are you trying to become?</h1>
          <span className="text-[14px] leading-[1.55] text-muted">Sarce measures distance from the style you pick, not from the engine.</span>
          <div className="flex flex-col gap-4" role="radiogroup" aria-label="Style goal">
            {GOALS.map((g) => (
              <button
                key={g.id}
                type="button"
                role="radio"
                aria-checked={goal === g.id}
                onClick={() => setGoal(g.id)}
                className={`grid grid-cols-[20px_minmax(0,1fr)] items-start gap-3 rounded-[8px] border-[1.5px] px-4 py-[14px] text-left ${
                  goal === g.id ? "border-accent bg-accent-tint" : "border-line-2 bg-surface"
                }`}
              >
                <span className="mt-[2px] grid h-4 w-4 place-items-center rounded-full border-[1.5px] border-ink">
                  <span className="h-2 w-2 rounded-full" style={{ background: goal === g.id ? "var(--accent)" : "transparent" }} />
                </span>
                <span className="flex flex-col gap-[3px]">
                  <span className="text-[15px] font-medium">{g.title}</span>
                  <span className="text-[13px] text-muted">{g.detail}</span>
                </span>
              </button>
            ))}
          </div>
        </>
      )}

      {step === 3 && (
        <>
          <h1 className="text-[26px] leading-[1.2] font-medium">One question per game, at most</h1>
          <span className="text-[14px] leading-[1.55] text-muted">
            After some games Sarce asks one thing: did it feel like you, what you meant, or a random check-in that tests whether its flags mean
            anything. Skip any of them, any time.
          </span>
          <div className="rounded-[8px] bg-panel px-[14px] py-3 text-[13px] leading-[1.5] text-ink-2">
            Your data stays on this device. Settings → What Sarce keeps.
          </div>
        </>
      )}

      {status && <span className="text-[13px] text-ink-2">{status}</span>}
      <div className="mt-2 flex items-center gap-[18px]">
        <PrimaryButton className="!px-[22px]" disabled={busy} onClick={next}>
          {busy ? "Connecting…" : step === 3 ? "Open Sarce" : "Continue"}
        </PrimaryButton>
        <TextButton className="!text-muted" onClick={() => (step > 0 ? setStep(step - 1) : router.back())}>
          Back
        </TextButton>
      </div>
    </div>
  );
}
