import type { UserBaseline } from "@/types/chess";

interface StyleSummaryProps {
  baseline: UserBaseline;
}

function inTargetRange(pct: number, min: number, max: number) {
  return pct >= min && pct <= max;
}

export function StyleSummary({ baseline }: StyleSummaryProps) {
  const { brilliantPct, targetBrilliantMin, targetBrilliantMax, gamesAnalyzed } =
    baseline;

  if (gamesAnalyzed === 0) {
    return (
      <div className="rounded-xl border border-white/10 bg-surface p-6">
        <h2 className="text-lg font-medium">Style summary</h2>
        <p className="mt-2 text-sm text-foreground/60">
          Import games to see how your Brilliant move rate compares to your
          Tal-inspired 6–10% target.
        </p>
      </div>
    );
  }

  const onTarget = inTargetRange(
    brilliantPct,
    targetBrilliantMin,
    targetBrilliantMax,
  );

  return (
    <div className="rounded-xl border border-white/10 bg-surface p-6">
      <h2 className="text-lg font-medium">Style summary</h2>
      <p className="mt-2 text-foreground/80">
        Across {gamesAnalyzed} analyzed games,{" "}
        <span className="font-semibold text-brilliant">
          {brilliantPct.toFixed(1)}%
        </span>{" "}
        of your moves were Brilliant.
        {onTarget ? (
          <span className="text-success">
            {" "}
            — right in your Tal-style target range.
          </span>
        ) : brilliantPct < targetBrilliantMin ? (
          <span className="text-warning">
            {" "}
            — below target; room to play more sacrificially.
          </span>
        ) : (
          <span className="text-foreground/60">
            {" "}
            — above target; check if sacrifices were sound.
          </span>
        )}
      </p>
    </div>
  );
}
