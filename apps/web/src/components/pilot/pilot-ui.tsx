import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";

export function PilotCard({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`rounded-[9px] border border-line bg-surface ${className}`} {...props} />;
}

export function PilotButton({ className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={`min-h-11 rounded-[7px] border border-ink bg-ink px-5 text-[14px] font-medium text-surface disabled:border-line-2 disabled:bg-line-2 disabled:text-muted ${className}`} {...props} />;
}

export function PilotProgress({ completed, target = 10 }: { completed: number; target?: number }) {
  return (
    <div className="grid grid-cols-10 gap-1" aria-label={`${completed} of ${target} style reads completed`}>
      {Array.from({ length: target }, (_, index) => (
        <span key={index} className={`h-[11px] rounded-[1px] border ${index < completed ? "border-ink bg-ink" : "border-line-2 bg-surface"}`} />
      ))}
    </div>
  );
}

export function PilotMessage({ children, role = "status" }: { children: ReactNode; role?: "status" | "alert" }) {
  return <p role={role} className="rounded-[7px] border border-line bg-panel px-4 py-3 text-[13px] leading-5">{children}</p>;
}
