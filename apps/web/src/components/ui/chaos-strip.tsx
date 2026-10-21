/**
 * Chaos you created, move by move: one bar per move, height from the chaos score.
 * High bars are mid-accent, the highlighted move (the brilliant one) full accent.
 */
export function ChaosStrip({
  values,
  highlight,
  max,
}: {
  /** One chaos score per move (any non-negative scale). */
  values: number[];
  /** Index of the move to draw in full accent. */
  highlight?: number | null;
  /** Value drawn at full height; defaults to the largest value. */
  max?: number;
}) {
  const top = max ?? Math.max(...values, 0);
  return (
    <div className="flex flex-col">
      <div className="flex h-9 items-end gap-[2px]" aria-hidden="true">
        {values.map((v, i) => {
          const share = top > 0 ? v / top : 0;
          const color = i === highlight ? "var(--accent)" : share >= 0.7 ? "var(--accent-mid)" : "var(--line-3)";
          return (
            <span
              key={i}
              className="min-h-[3px] flex-1 rounded-t-[2px]"
              style={{ height: `${share * 90}%`, background: color }}
            />
          );
        })}
      </div>
      <span className="mt-1.5 flex justify-between font-mono text-[10px] text-muted">
        <span>chaos you created, move by move</span>
        <span>{values.length} moves</span>
      </span>
    </div>
  );
}
