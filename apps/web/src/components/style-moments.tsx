import type { StyleMoment } from "@/types/chess";

interface StyleMomentsProps {
  moments: StyleMoment[];
}

const QUALITY_LABELS: Record<StyleMoment["quality"], string> = {
  best: "Best",
  excellent: "Excellent",
  good: "Good",
  inaccuracy: "Inaccuracy",
  mistake: "Mistake",
  blunder: "Blunder",
  miss: "Miss",
  brilliant: "Brilliant",
};

const QUALITY_STYLES: Record<StyleMoment["quality"], string> = {
  brilliant: "border-brilliant/40 bg-brilliant/10 text-brilliant",
  miss: "border-rose-300/30 bg-rose-400/10 text-rose-200",
  blunder: "border-red-300/30 bg-red-500/10 text-red-200",
  mistake: "border-orange-300/30 bg-orange-400/10 text-orange-200",
  inaccuracy: "border-yellow-300/30 bg-yellow-400/10 text-yellow-100",
  best: "border-emerald-300/30 bg-emerald-500/10 text-emerald-200",
  excellent: "border-green-300/30 bg-green-400/10 text-green-200",
  good: "border-sky-300/30 bg-sky-400/10 text-sky-200",
};

function formatMoveNumber(ply: number) {
  const move = Math.floor(ply / 2) + 1;
  return ply % 2 === 0 ? `${move}.` : `${move}...`;
}

function formatEval(value: number | null) {
  if (value === null) return "?";
  return value > 0 ? `+${value.toFixed(1)}` : value.toFixed(1);
}

export function StyleMoments({ moments }: StyleMomentsProps) {
  return (
    <section className="rounded-lg border border-white/10 bg-surface p-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 className="text-lg font-medium">Recent style moments</h2>
          <p className="mt-1 text-sm text-foreground/50">
            Brilliant moves, misses, and sharp turns from analyzed games.
          </p>
        </div>
      </div>

      {moments.length === 0 ? (
        <p className="mt-6 text-sm text-foreground/40">
          Analyze games to surface notable moves.
        </p>
      ) : (
        <ul className="mt-5 divide-y divide-white/10">
          {moments.map((moment) => (
            <li
              key={`${moment.gameId}-${moment.ply}`}
              className="grid gap-3 py-4 md:grid-cols-[120px_1fr_170px]"
            >
              <div>
                <span
                  className={`inline-flex rounded-md border px-2 py-1 text-xs font-medium ${QUALITY_STYLES[moment.quality]}`}
                >
                  {QUALITY_LABELS[moment.quality]}
                </span>
              </div>
              <div className="min-w-0">
                <p className="font-mono text-sm text-foreground">
                  {formatMoveNumber(moment.ply)} {moment.san ?? moment.uci}
                </p>
                <p className="mt-1 truncate text-sm text-foreground/50">
                  {moment.highlight ?? `vs ${moment.opponent ?? "unknown opponent"}`}
                  {moment.result ? ` - ${moment.result}` : ""}
                </p>
                {moment.signals.length > 0 && (
                  <p className="mt-1 truncate text-xs text-foreground/40">
                    {moment.signals.slice(0, 3).join(" / ")}
                  </p>
                )}
              </div>
              <div className="text-sm text-foreground/60 md:text-right">
                <p className="tabular-nums">
                  {formatEval(moment.evalBefore)} to {formatEval(moment.evalAfter)}
                </p>
                {moment.cpLoss !== null && moment.quality !== "brilliant" && (
                  <p className="mt-1 text-xs text-foreground/40">
                    {moment.cpLoss.toFixed(0)} cp loss
                  </p>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
