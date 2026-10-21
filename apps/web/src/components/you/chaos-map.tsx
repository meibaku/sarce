"use client";

import { useCallback, useEffect, useState } from "react";
import { TextButton } from "@/components/ui/buttons";
import { Board } from "@/components/ui/board";
import { Card, SectionLabel } from "@/components/ui/card";
import { getChaosMap, rebuildChaosMap, type ChaosMapPosition } from "@/lib/api";

/*
 * Your chaos map (app/services/chaos_map.py): the opening positions you reach most, and in each the one sound
 * move that sets your opponents the hardest problem. Predictable openings are the point: you know the position
 * is coming, so you can prepare the one move that asks a real question. A mirror, not a verdict: your usual
 * move is shown beside it, never marked wrong.
 */

const pct = (v: number | null) => (v == null ? "–" : `${Math.round(v * 100)}%`);
/** How much bigger a problem the chaos move sets than your usual move (expected points). */
const gain = (p: ChaosMapPosition) => (p.same ? 0 : (p.chaos.problem ?? 0) - (p.usual.problem ?? 0));
/** Below this the two moves ask about the same of the opponent: not worth changing a habit for. */
const WORTH_IT = 0.02;

function Row({ p, on, onPick }: { p: ChaosMapPosition; on: boolean; onPick: () => void }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onPick}
      className={`grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-t border-hair py-[10px] text-left ${on ? "text-ink" : "text-ink-2 hover:text-ink"}`}
    >
      <span className="flex min-w-0 flex-col gap-[2px]">
        <span className="truncate font-mono text-[12px]">{p.line}</span>
        <span className="text-[12px] text-muted">
          reached {p.seen}× · you play {p.usual.san}
        </span>
      </span>
      <span className={`font-mono text-[13px] font-medium ${gain(p) < WORTH_IT ? "text-sound" : "text-accent-text"}`}>
        {gain(p) < WORTH_IT ? `${p.usual.san} ✓` : p.chaos.san}
      </span>
    </button>
  );
}

function Detail({ p }: { p: ChaosMapPosition }) {
  const orientation = p.fen.split(" ")[1] === "b" ? "black" : "white";
  const hot = [p.chaos.uci.slice(0, 2), p.chaos.uci.slice(2, 4)];
  return (
    <div className="flex flex-wrap items-start gap-5">
      <Board compact fen={p.fen} orientation={orientation} hot={hot} label={`Chaos move ${p.chaos.san} after ${p.line}`} />
      <div className="flex min-w-[220px] flex-1 flex-col gap-3 text-[13px] leading-[1.5]">
        <span className="text-[15px] font-medium">
          {p.same
            ? `${p.chaos.san} is already your move here.`
            : gain(p) < WORTH_IT
              ? `Your ${p.usual.san} asks about as much as anything here.`
              : `Try ${p.chaos.san} instead of ${p.usual.san}.`}
        </span>
        <span className="text-ink-2">
          {p.predictability != null && `Opponents steer into this position ${pct(p.predictability)} of the time, so you can prepare for it. `}
          After {p.chaos.san}, a player near {p.elo} misses every safe reply {pct(p.chaos.pFail)} of the time
          {p.chaos.stake ? `, and a miss costs them about ${Math.round(p.chaos.stake * 100)}% of their expected score` : ""}.
        </span>
        <div className="grid grid-cols-[auto_auto_auto] gap-x-4 gap-y-1 font-mono text-[12px]">
          <span className="text-muted">move</span>
          <span className="text-muted">miss rate</span>
          <span className="text-muted">problem</span>
          <span className="text-accent-text">{p.chaos.san}</span>
          <span>{pct(p.chaos.pFail)}</span>
          <span>{p.chaos.problem?.toFixed(2) ?? "–"}</span>
          {!p.same && (
            <>
              <span>{p.usual.san} (yours)</span>
              <span>{pct(p.usual.pFail)}</span>
              <span>{p.usual.problem?.toFixed(2) ?? "–"}</span>
            </>
          )}
        </div>
        <span className="text-[12px] text-muted">
          {p.chaos.epLoss ? `Sound: within ${Math.round(p.chaos.epLoss * 100)}% of the engine's best.` : "Sound: the engine's own top choice."}
          {p.elo === 800 ? " 800 is the human model's lowest step, so below it the miss rate is, if anything, higher." : ""}
        </span>
      </div>
    </div>
  );
}

export function ChaosMapCard() {
  const [positions, setPositions] = useState<ChaosMapPosition[] | null>(null);
  const [building, setBuilding] = useState(false);
  const [pick, setPick] = useState(0);

  const load = useCallback(() => {
    getChaosMap()
      .then((d) => {
        // Biggest gain first: the move most worth adding to your repertoire leads.
        setPositions([...d.positions].sort((a, b) => gain(b) - gain(a)));
        setBuilding(d.building);
      })
      .catch(() => setPositions([]));
  }, []);

  useEffect(load, [load]);
  // While the API rebuilds (a minute or two of engine work), check back every few seconds.
  useEffect(() => {
    if (!building) return;
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [building, load]);

  const rebuild = () => {
    setBuilding(true);
    rebuildChaosMap().catch(() => setBuilding(false));
  };

  const current = positions?.[pick] ?? positions?.[0];
  return (
    <Card className="gap-3">
      <div className="flex flex-wrap items-baseline gap-3">
        <SectionLabel className="flex-1">Your chaos map · openings</SectionLabel>
        <TextButton onClick={rebuild} disabled={building}>
          {building ? "Reading your games…" : positions?.length ? "Rebuild" : "Build my map"}
        </TextButton>
      </div>
      <span className="text-[13px] leading-[1.5] text-ink-2">
        The positions you reach again and again, and the one sound move in each that sets your opponents the hardest problem.
      </span>
      {positions === null ? null : positions.length === 0 ? (
        <span className="text-[13px] text-muted">{building ? "Reading your openings: this takes a minute or two." : "No map yet."}</span>
      ) : (
        <>
          {current && <Detail p={current} />}
          <div className="flex flex-col">
            {positions.map((p, i) => (
              <Row key={p.fen} p={p} on={p === current} onPick={() => setPick(i)} />
            ))}
          </div>
        </>
      )}
    </Card>
  );
}
