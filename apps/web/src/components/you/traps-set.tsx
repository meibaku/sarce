"use client";

import { useCallback, useEffect, useState } from "react";
import { TextButton } from "@/components/ui/buttons";
import { Board } from "@/components/ui/board";
import { Card, SectionLabel } from "@/components/ui/card";
import { getTrapsSet, rebuildTrapsSet, type TrapSet } from "@/lib/api";

/*
 * Your traps (app/services/traps_set.py): the opening positions you steer into where opponents most often go wrong
 * on the very next move, from your own finished games. The attacking side of the trap atlas, and the partner of the
 * chaos map: one move gets you a likely edge, the trap catches the players who miss it.
 */

const pct = (v: number) => `${Math.round(v * 100)}%`;

export function TrapsSetCard() {
  const [traps, setTraps] = useState<TrapSet[] | null>(null);
  const [building, setBuilding] = useState(false);
  const [pick, setPick] = useState(0);

  const load = useCallback(() => {
    getTrapsSet()
      .then((d) => {
        setTraps(d.traps);
        setBuilding(d.building);
      })
      .catch(() => setTraps([]));
  }, []);

  useEffect(load, [load]);
  useEffect(() => {
    if (!building) return;
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [building, load]);

  const current = traps?.[pick] ?? traps?.[0];
  return (
    <Card className="gap-3">
      <div className="flex flex-wrap items-baseline gap-3">
        <SectionLabel className="flex-1">Your traps · openings</SectionLabel>
        <TextButton
          onClick={() => {
            setBuilding(true);
            rebuildTrapsSet().catch(() => setBuilding(false));
          }}
          disabled={building}
        >
          {building ? "Reading your games…" : traps?.length ? "Rebuild" : "Find my traps"}
        </TextButton>
      </div>
      <span className="text-[13px] leading-[1.5] text-ink-2">
        Positions you steer into where opponents most often go wrong on the very next move.
      </span>
      {traps === null ? null : traps.length === 0 ? (
        <span className="text-[13px] text-muted">{building ? "Reading your openings: under a minute, no engine needed." : "No traps found yet."}</span>
      ) : (
        <>
          {current && (
            <div className="flex flex-wrap items-start gap-5">
              <Board
                compact
                fen={current.fen}
                orientation={current.fen.split(" ")[1] === "b" ? "white" : "black"}
                label={`Your trap after ${current.line}`}
              />
              <div className="flex min-w-[220px] flex-1 flex-col gap-2 text-[13px] leading-[1.5]">
                <span className="text-[15px] font-medium">
                  After {current.move}, {pct(current.rate)} of opponents went wrong.
                </span>
                <span className="text-ink-2">
                  Caught {current.caught} of {current.seen}. The usual slip is {current.slip}, worth about {current.gainPawns.toFixed(1)} pawns to you.
                  The defence that holds is {current.defence}.
                </span>
                <span className="font-mono text-[11px] text-muted">{current.line}</span>
              </div>
            </div>
          )}
          <div className="flex flex-col">
            {traps.map((t, i) => (
              <button
                key={t.fen}
                type="button"
                aria-pressed={t === current}
                onClick={() => setPick(i)}
                className={`grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-t border-hair py-[10px] text-left ${t === current ? "text-ink" : "text-ink-2 hover:text-ink"}`}
              >
                <span className="flex min-w-0 flex-col gap-[2px]">
                  <span className="truncate font-mono text-[12px]">{t.line}</span>
                  <span className="text-[12px] text-muted">
                    caught {t.caught} of {t.seen} · they slip with {t.slip}
                  </span>
                </span>
                <span className="font-mono text-[13px] font-medium text-accent-text">{pct(t.rate)}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </Card>
  );
}
