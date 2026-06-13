interface BrilliantGaugeProps {
  brilliantPct: number;
  targetMin: number;
  targetMax: number;
}

export function BrilliantGauge({
  brilliantPct,
  targetMin,
  targetMax,
}: BrilliantGaugeProps) {
  const maxScale = 20;
  const fillPct = Math.min((brilliantPct / maxScale) * 100, 100);
  const targetStart = (targetMin / maxScale) * 100;
  const targetWidth = ((targetMax - targetMin) / maxScale) * 100;

  return (
    <div className="rounded-xl border border-white/10 bg-surface p-6">
      <p className="text-xs uppercase tracking-wider text-foreground/50">
        Headline metric
      </p>
      <h2 className="mt-1 text-lg font-medium text-brilliant">Brilliant %</h2>
      <p className="mt-4 text-4xl font-semibold tabular-nums">
        {brilliantPct.toFixed(1)}
        <span className="text-lg text-foreground/50">%</span>
      </p>
      <p className="mt-1 text-sm text-foreground/50">
        Target: {targetMin}–{targetMax}%
      </p>

      <div className="relative mt-6 h-3 overflow-hidden rounded-full bg-background">
        <div
          className="absolute inset-y-0 rounded-full bg-brilliant/30"
          style={{ left: `${targetStart}%`, width: `${targetWidth}%` }}
        />
        <div
          className="h-full rounded-full bg-brilliant transition-all"
          style={{ width: `${fillPct}%` }}
        />
      </div>
    </div>
  );
}
