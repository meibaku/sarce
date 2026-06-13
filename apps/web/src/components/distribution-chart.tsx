import type { MoveQualityDistribution } from "@/types/chess";

const LABELS: { key: keyof MoveQualityDistribution; label: string; color: string }[] = [
  { key: "brilliant", label: "Brilliant", color: "bg-brilliant" },
  { key: "best", label: "Best", color: "bg-emerald-500" },
  { key: "excellent", label: "Excellent", color: "bg-green-400" },
  { key: "good", label: "Good", color: "bg-sky-400" },
  { key: "inaccuracy", label: "Inaccuracy", color: "bg-yellow-400" },
  { key: "mistake", label: "Mistake", color: "bg-orange-400" },
  { key: "blunder", label: "Blunder", color: "bg-red-500" },
  { key: "miss", label: "Miss", color: "bg-rose-400" },
];

interface DistributionChartProps {
  title: string;
  distribution: MoveQualityDistribution;
  gamesAnalyzed: number;
  subtitle?: string;
}

export function DistributionChart({
  title,
  distribution,
  gamesAnalyzed,
  subtitle,
}: DistributionChartProps) {
  const total = Object.values(distribution).reduce((a, b) => a + b, 0);

  return (
    <div className="rounded-xl border border-white/10 bg-surface p-6">
      <h2 className="text-lg font-medium">{title}</h2>
      {subtitle && (
        <p className="mt-1 text-sm text-foreground/50">{subtitle}</p>
      )}
      {gamesAnalyzed > 0 && (
        <p className="mt-1 text-xs text-foreground/40">
          {gamesAnalyzed} games sampled
        </p>
      )}

      {total === 0 ? (
        <p className="mt-6 text-sm text-foreground/40">No data yet</p>
      ) : (
        <ul className="mt-6 space-y-3">
          {LABELS.map(({ key, label, color }) => {
            const count = distribution[key];
            const pct = total > 0 ? (count / total) * 100 : 0;
            return (
              <li key={key} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span>{label}</span>
                  <span className="tabular-nums text-foreground/60">
                    {pct.toFixed(1)}%
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-background">
                  <div
                    className={`h-full rounded-full ${color}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
