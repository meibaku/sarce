/**
 * Brilliant gauge (docs/DESIGN.md): a 10px track on a 0–15% scale, the user's goal band in
 * accent tint, a 2px ink marker at the current value, an optional ±range hatch and an optional
 * grey marker for the rolling average, and an optional dashed outline for the personal next band (the step just
 * above your likely range). Every gauge in the app follows the user's goal.
 */
const SCALE = 15;

const pct = (x: number) => `${(Math.max(0, Math.min(SCALE, x)) / SCALE) * 100}%`;

export interface StyleGaugeProps {
  /** Current value; null hides the marker when there are too few games. */
  value: number | null;
  goalLo: number;
  goalHi: number;
  /** ± spread around the value, drawn as a 2px-on / 2px-off hatch. */
  spread?: number;
  /** Rolling average, drawn as a grey marker. */
  average?: number;
  /** Your next band, drawn as a dashed accent outline. */
  next?: { lo: number; hi: number } | null;
  label?: string;
  /** The small Summary variant: 8px track, no scale labels. */
  compact?: boolean;
}

export function StyleGauge({ value, goalLo, goalHi, spread, average, next, label = "Brilliant %", compact = false }: StyleGaugeProps) {
  const nextLabel = next ? `, next band ${next.lo}–${next.hi}%` : "";
  return (
    <div className="flex flex-col gap-3" role="img" aria-label={`${label}: ${value == null ? "not enough games yet" : `${value.toFixed(1)}%`}, goal ${goalLo}–${goalHi}%${nextLabel}`}>
      <div className={`relative box-content border-[1.5px] border-ink ${compact ? "h-2 rounded-[5px]" : "h-[10px] rounded-[6px]"}`}>
        <div
          className="absolute top-[-1.5px] bottom-[-1.5px] border-[1.5px] border-accent bg-accent-tint"
          style={{ left: pct(goalLo), width: pct(goalHi - goalLo) }}
        />
        {next && (
          <div
            className="absolute top-[-1.5px] bottom-[-1.5px] min-w-[3px] border-[1.5px] border-dashed border-accent"
            style={{ left: pct(next.lo), width: pct(next.hi - next.lo) }}
          />
        )}
        {value != null && spread != null && spread > 0 && (
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
            className={`absolute -ml-px w-[2px] bg-line-3 ${compact ? "top-[-4px] bottom-[-4px]" : "top-[-5px] bottom-[-5px] rounded-[1px]"}`}
            style={{ left: pct(average) }}
          />
        )}
        {value != null && (
          <div
            className={`absolute -ml-px w-[2px] bg-ink ${compact ? "top-[-6px] bottom-[-6px]" : "top-[-7px] bottom-[-7px] rounded-[1px]"}`}
            style={{ left: pct(value) }}
          />
        )}
      </div>
      <div className={`relative h-3 font-mono text-[10px] text-muted ${compact ? "hidden" : ""}`}>
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
