/**
 * Brilliant gauge (docs/DESIGN.md): a 10px track on a 0–15% scale, the user's goal band in
 * accent tint, a 2px ink marker at the current value, an optional ±range hatch and an optional
 * grey marker for the rolling average. Every gauge in the app follows the user's goal.
 */
const SCALE = 15;

const pct = (x: number) => `${(Math.max(0, Math.min(SCALE, x)) / SCALE) * 100}%`;

export interface StyleGaugeProps {
  value: number;
  goalLo: number;
  goalHi: number;
  /** ± spread around the value, drawn as a 2px-on / 2px-off hatch. */
  spread?: number;
  /** Rolling average, drawn as a grey marker. */
  average?: number;
  label?: string;
}

export function StyleGauge({ value, goalLo, goalHi, spread, average, label = "Brilliant %" }: StyleGaugeProps) {
  return (
    <div className="flex flex-col gap-3" role="img" aria-label={`${label}: ${value.toFixed(1)}%, goal ${goalLo}–${goalHi}%`}>
      <div className="relative box-content h-[10px] rounded-[6px] border-[1.5px] border-ink">
        <div
          className="absolute top-[-1.5px] bottom-[-1.5px] border-[1.5px] border-accent bg-accent-tint"
          style={{ left: pct(goalLo), width: pct(goalHi - goalLo) }}
        />
        {spread != null && spread > 0 && (
          <div
            className="absolute top-px bottom-px"
            style={{
              left: pct(value - spread),
              width: pct(Math.min(value + spread, SCALE) - Math.max(value - spread, 0)),
              background: "repeating-linear-gradient(90deg, var(--line-3) 0 2px, transparent 2px 4px)",
            }}
          />
        )}
        {average != null && (
          <div
            className="absolute top-[-5px] bottom-[-5px] -ml-px w-[2px] rounded-[1px] bg-line-3"
            style={{ left: pct(average) }}
          />
        )}
        <div className="absolute top-[-7px] bottom-[-7px] -ml-px w-[2px] rounded-[1px] bg-ink" style={{ left: pct(value) }} />
      </div>
      <div className="relative h-3 font-mono text-[10px] text-muted">
        <span className="absolute left-0">0</span>
        <span className="absolute -translate-x-1/2" style={{ left: pct(goalLo) }}>
          {goalLo}
        </span>
        <span className="absolute -translate-x-1/2" style={{ left: pct(goalHi) }}>
          {goalHi}
        </span>
        <span className="absolute right-0">15%</span>
      </div>
    </div>
  );
}
