"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { SarceMark } from "@/components/ui/icons";
import { usePilotStatus } from "@/components/pilot/pilot-status";

const NAV = [
  { label: "Home", short: "Home", href: "/" },
  { label: "Games and review", short: "Games", href: "/games" },
  { label: "Pilot progress", short: "Progress", href: "/pilot/progress" },
  { label: "Account and privacy", short: "Account", href: "/account" },
];

function active(path: string, href: string) {
  if (href === "/") return path === "/";
  if (href === "/games") return path.startsWith("/games");
  return path.startsWith(href);
}

function windowLabel(startsAt: string | null, endsAt: string | null) {
  if (!startsAt || !endsAt) return "Style pilot";
  const now = Date.now();
  const start = new Date(startsAt).getTime();
  const end = new Date(endsAt).getTime();
  const day = Math.min(14, Math.max(1, Math.floor((now - start) / 86_400_000) + 1));
  const left = Math.max(0, Math.ceil((end - now) / 86_400_000));
  return `Day ${day} of 14 · ${left} days left`;
}

export function PilotShell({ children }: { children: ReactNode }) {
  const pathname = usePathname() ?? "/";
  const { status, offline, error } = usePilotStatus();
  const terminal = status && status.state !== "active" && status.state !== "invited";
  const label = windowLabel(status?.startsAt ?? null, status?.endsAt ?? null);

  return (
    <div data-pilot-shell className="flex min-h-dvh flex-col bg-page text-ink">
      <header className="border-b border-line bg-page">
        <div className="mx-auto flex h-[60px] max-w-[1080px] items-center gap-5 px-5">
          <Link href="/" className="flex min-h-11 items-center gap-2" aria-label="Sarce pilot home">
            <SarceMark height={23} />
            <span className="text-[19px] font-medium">sarce</span>
          </Link>
          <span className="rounded-full border border-line-2 px-2 py-1 font-mono text-[11px]">Style pilot</span>
          <nav className="hidden self-stretch md:flex" aria-label="Pilot">
            {NAV.map((item) => (
              <Link key={item.href} href={item.href} aria-current={active(pathname, item.href) ? "page" : undefined}
                className={`flex min-h-11 items-center border-b-2 px-3 text-[13px] font-medium ${active(pathname, item.href) ? "border-ink" : "border-transparent text-ink-2"}`}>
                {item.label}
              </Link>
            ))}
          </nav>
          <span className="ml-auto font-mono text-[11px] text-muted">{label}</span>
        </div>
      </header>
      <div aria-live="polite">
        {offline && <div className="border-b border-line bg-panel px-5 py-2 text-center text-[13px]">You are offline. Drafts stay on this device until you retry.</div>}
        {error && <div className="border-b border-line bg-panel px-5 py-2 text-center text-[13px]">Sarce could not refresh pilot status. Reference {error}.</div>}
        {terminal && <div className="border-b border-line bg-panel px-5 py-2 text-center text-[13px]">This pilot is {status.state}. Your existing reads, export and deletion remain available.</div>}
      </div>
      <div className="flex-1 pb-20 md:pb-0">{children}</div>
      <nav className="fixed inset-x-0 bottom-0 z-30 grid h-[72px] grid-cols-4 border-t border-line bg-surface md:hidden" aria-label="Pilot">
        {NAV.map((item) => (
          <Link key={item.href} href={item.href} aria-current={active(pathname, item.href) ? "page" : undefined}
            className={`grid min-h-11 place-items-center text-[12px] font-medium ${active(pathname, item.href) ? "text-ink" : "text-muted"}`}>
            {item.short}
          </Link>
        ))}
      </nav>
    </div>
  );
}
