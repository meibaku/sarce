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
