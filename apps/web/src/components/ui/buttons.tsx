import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

/*
 * Action rules (docs/DESIGN.md): exactly one PrimaryButton per screen — the next step in
 * the loop. Choices are ChoiceButtons; every other action is a TextLink.
 */

const primary =
  "inline-flex h-11 items-center justify-center rounded-[6px] border-0 bg-accent px-[18px] text-[13px] font-medium text-white transition-colors duration-[120ms] ease-sarce hover:bg-accent-hover active:bg-accent-active cursor-pointer";

const textLink =
  "inline-flex items-center border-0 bg-transparent p-0 text-[13px] font-medium text-accent-text hover:underline cursor-pointer";

type ButtonProps = ComponentProps<"button">;

export function PrimaryButton({ className = "", ...props }: ButtonProps) {
  return <button type="button" className={`${primary} ${className}`} {...props} />;
}

export function PrimaryLink({ className = "", ...props }: ComponentProps<typeof Link>) {
  return <Link className={`${primary} ${className}`} {...props} />;
}

export function TextButton({ className = "", ...props }: ButtonProps) {
  return <button type="button" className={`${textLink} ${className}`} {...props} />;
}

export function TextLink({ className = "", ...props }: ComponentProps<typeof Link>) {
  return <Link className={`${textLink} ${className}`} {...props} />;
}

/** Outlined choice or toggle: ink outline when chosen, line-2 otherwise; `selected` is the accent state. */
export function ChoiceButton({
  chosen = false,
  selected = false,
  className = "",
  children,
  ...props
}: ButtonProps & { chosen?: boolean; selected?: boolean; children: ReactNode }) {
  const state = selected
    ? "border-accent bg-accent-tint text-accent-text"
    : chosen
      ? "border-ink bg-surface text-ink"
      : "border-line-2 bg-surface text-ink";
  return (
    <button
      type="button"
      aria-pressed={chosen || selected}
      className={`rounded-[6px] border-[1.5px] text-[13px] font-medium transition-colors duration-[120ms] ease-sarce hover:bg-panel active:bg-press cursor-pointer ${state} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

/** 44×24 switch with a 1.5px ink outline (handoff Settings). */
export function Switch({ on, onChange, label }: { on: boolean; onChange: (next: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      onClick={() => onChange(!on)}
      className={`relative h-6 w-11 flex-none rounded-[12px] border-[1.5px] border-ink p-0 ${on ? "bg-accent" : "bg-surface"}`}
    >
      <span
        className={`absolute top-[2px] h-[17px] w-[17px] rounded-full transition-[left] duration-[120ms] ease-sarce ${on ? "left-[22px] bg-surface" : "left-[2px] bg-ink"}`}
      />
    </button>
  );
}

/** − value + stepper, 36px square buttons. */
export function Stepper({
  label,
  value,
  onChange,
  min,
  max,
  suffix = "",
}: {
  label: string;
  value: number;
  onChange: (next: number) => void;
  min: number;
  max: number;
  suffix?: string;
}) {
  const step = "h-9 w-9 rounded-[6px] border-[1.5px] border-line-2 bg-surface font-mono text-[16px] font-medium hover:bg-panel active:bg-press";
  return (
    <div className="flex items-center gap-2">
      <span className="w-9 text-[13px] text-muted">{label}</span>
      <button type="button" className={step} aria-label={`Lower ${label}`} onClick={() => onChange(Math.max(min, value - 1))}>
        −
      </button>
      <span className="min-w-11 text-center font-mono text-[20px] text-accent-text" aria-live="polite">
        {value}
        {suffix}
      </span>
      <button type="button" className={step} aria-label={`Raise ${label}`} onClick={() => onChange(Math.min(max, value + 1))}>
        +
      </button>
    </div>
  );
}
