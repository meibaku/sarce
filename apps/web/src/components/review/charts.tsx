import type { ReviewApi } from "@/types/chess";

const RUNGS = [800, 1200, 1600, 2000, 2400];

/** "Who falls for this": P_fail at the five ladder ratings, as in the handoff (300×112 frame). */
export function FallsChart({ pFail }: { pFail: number[] }) {
  const pts = pFail.map((p, i) => ({ x: i * 70 + 10, y: 110 - p * 100, p }));
  return (
    <div className="flex flex-col gap-[10px]">
      <div className="relative w-full" style={{ aspectRatio: "300 / 112" }}>
        <svg viewBox="0 0 300 112" preserveAspectRatio="none" className="absolute inset-0 h-full w-full" aria-hidden="true">
          <line x1="0" y1="110" x2="300" y2="110" stroke="var(--ink)" strokeWidth="1.25" />
          <line x1="0" y1="60" x2="300" y2="60" stroke="var(--hair)" />
          <polyline
            points={pts.map((pt) => `${pt.x},${pt.y}`).join(" ")}
            fill="none"
            stroke="var(--accent)"
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
        {pts.map((pt, i) => {
          const style = { left: `${(pt.x / 300) * 100}%`, top: `${(pt.y / 112) * 100}%` };
          return (
            <span key={RUNGS[i]}>
              <span className="absolute -mt-[5px] -ml-[5px] h-[9px] w-[9px] rounded-full border-[1.75px] border-accent bg-surface" style={style} />
              <span className="absolute -translate-x-1/2 -translate-y-[22px] font-mono text-[10px] text-accent-text" style={style}>
                {Math.round(pt.p * 100)}%
              </span>
            </span>
          );
        })}
      </div>
      <div className="flex justify-between font-mono text-[10px] text-muted">
        {RUNGS.map((r) => (
          <span key={r}>{r}</span>
        ))}
      </div>
    </div>
  );
}

const FAMILY: Record<string, string> = { gambit: "gambit", king_attack: "kingside attack", squeeze: "squeeze" };

/** Idea arcs from the intention tagger: landed ideas solid accent, the rest dashed grey. */
export function IdeaArcs({ ideas, plies }: { ideas: ReviewApi["ideas"]; plies: number }) {
  if (ideas.length === 0 || plies === 0) return null;
  const x = (ply: number) => Math.max(0, Math.min(340, (ply / plies) * 340));
  const landed = ideas.filter((i) => i.verdict === "worked").length;
  const first = Math.floor(ideas[0].startPly / 2) + 1;
  const last = Math.floor(ideas[ideas.length - 1].endPly / 2) + 1;
  const rest = ideas.length - landed;
  const caption = `Moves ${first}–${last}: ${landed} plan${landed === 1 ? "" : "s"} that landed${
    rest ? `, ${rest} that ${rest === 1 ? "was" : "were"} met or faded` : ""
  }.`;

  return (
    <div className="flex flex-col gap-[6px] rounded-[8px] border border-line bg-surface px-[14px] py-3">
      <span className="font-mono text-[10px] text-muted">IDEA ARCS · from the tagger</span>
      <svg viewBox="0 0 340 54" className="h-auto w-full overflow-visible" aria-label={caption} role="img">
        <line x1="0" y1="44" x2="340" y2="44" stroke="var(--line-2)" strokeWidth="1.5" />
        {ideas.map((idea, i) => {
          const a = x(idea.startPly);
          const b = x(idea.endPly);
          const mid = (a + b) / 2;
          // As in the handoff: the control point rises ~0.37 of the arc's length (max 40).
          const rise = Math.max(12, Math.min(40, (b - a) * 0.37));
          const solid = idea.verdict === "worked" && !idea.isPivot;
          const color = solid ? "var(--accent)" : "var(--muted)";
          const label = idea.isPivot ? "pivot" : `${FAMILY[idea.family] ?? idea.family} · ${solid ? "landed" : idea.verdict === "refuted" ? "met" : "faded"}`;
          return (
            <g key={i}>
              <path d={`M${a} 44 Q${mid} ${44 - rise} ${b} 44`} fill="none" stroke={color} strokeWidth="1.75" strokeDasharray={solid ? undefined : "3 3"} />
              <circle cx={b} cy="44" r="3.5" fill={solid ? "var(--accent)" : "var(--surface)"} stroke={solid ? "none" : "var(--muted)"} strokeWidth="1.5" />
              <text x={mid} y={44 - rise / 2 - 10} textAnchor="middle" fontFamily="var(--font-plex-mono)" fontSize="9" fill={solid ? "var(--accent-text)" : "var(--muted)"}>
                {label}
              </text>
            </g>
          );
        })}
      </svg>
      <span className="text-[12px] text-muted">{caption}</span>
    </div>
  );
}
