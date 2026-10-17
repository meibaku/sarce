import type { ComponentProps, ReactNode } from "react";

/** White card: 1px line hairline, or the 1.5px ink outline for the card that leads a screen. */
export function Card({
  lead = false,
  className = "",
  ...props
}: ComponentProps<"section"> & { lead?: boolean }) {
  const border = lead ? "border-[1.5px] border-ink" : "border border-line";
  return (
    <section
      className={`flex flex-col rounded-[8px] bg-surface px-[22px] py-5 ${border} ${className}`}
      {...props}
    />
  );
}

export function SectionLabel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <span className={`text-[11px] font-semibold uppercase tracking-[0.08em] text-muted ${className}`}>
      {children}
    </span>
  );
}

/** Small mono label over a mono value, as in the Home stats row. */
export function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <span className="flex flex-col gap-px">
      <span className="font-mono text-[10px] text-muted">{label}</span>
      <span className="font-mono text-[15px]">{value}</span>
    </span>
  );
}

/** Responsive grid that stacks on phone and splits on desktop (handoff layout rule). */
export function AutoGrid({
  min,
  className = "",
  ...props
}: ComponentProps<"div"> & { min: number }) {
  return (
    <div
      className={`grid gap-3 md:gap-[18px] ${className}`}
      style={{ gridTemplateColumns: `repeat(auto-fit, minmax(min(100%, ${min}px), 1fr))` }}
      {...props}
    />
  );
}
