"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Icon, SarceMark, type IconName } from "@/components/ui/icons";

/*
 * App frame from the v1.0 handoff. Desktop (md and up): a 56px white header with the mark,
 * five nav buttons, the account line and Settings. Phone: a compact header with the screen
 * title and a five-tab bar at the bottom. Content scrolls between them.
 */

const NAV: { id: IconName; label: string; href: string }[] = [
  { id: "home", label: "Home", href: "/" },
  { id: "review", label: "Review", href: "/review" },
  { id: "you", label: "You", href: "/you" },
  { id: "train", label: "Train", href: "/train" },
  { id: "play", label: "Play", href: "/play" },
];

/** Which nav item a route belongs to: Summary sits under Review, Library and Recap under You. */
export function activeNav(pathname: string): IconName | null {
  if (pathname === "/" || pathname.startsWith("/onboarding") || pathname.startsWith("/preview/home")) return "home";
  if (pathname.startsWith("/games") || pathname.startsWith("/review")) return "review";
  if (pathname.startsWith("/you") || pathname.startsWith("/library") || pathname.startsWith("/recap")) return "you";
  if (pathname.startsWith("/train")) return "train";
  if (pathname.startsWith("/play")) return "play";
  return null;
}

function SettingsButton({ size, active }: { size: number; active: boolean }) {
  return (
    <Link
      href="/settings"
      aria-label="Settings"
      className={`grid place-items-center rounded-[6px] border-[1.5px] text-ink transition-colors duration-[120ms] ease-sarce hover:bg-panel ${
        active ? "border-accent bg-accent-tint" : "border-line-2 bg-surface"
      }`}
      style={{ width: size, height: size }}
    >
      <Icon name="settings" size={17} />
    </Link>
  );
}

export function AppShell({
  title,
  account,
  children,
}: {
  /** Phone header subtitle, e.g. "home" or "review · m_volkov". */
  title: string;
  /** Desktop header account line, e.g. "kestrel_9 · Chess.com · synced 2 min ago". */
  account?: string;
  children: ReactNode;
}) {
  const pathname = usePathname() ?? "/";
  const current = activeNav(pathname);
  const onSettings = pathname.startsWith("/settings");

  return (
    <div className="flex h-dvh flex-col bg-page text-ink">
      <header className="hidden h-14 flex-none items-center gap-6 border-b border-line bg-surface px-7 md:flex">
        <Link href="/" className="flex items-center gap-2 text-ink" aria-label="Sarce home">
          <SarceMark height={24} framed />
          <span className="text-[19px] font-medium tracking-[-0.02em]">sarce</span>
        </Link>
        <nav className="flex gap-1" aria-label="Main">
          {NAV.map((item) => {
            const on = current === item.id;
            return (
              <Link
                key={item.id}
                href={item.href}
                aria-current={on ? "page" : undefined}
                className={`flex h-[34px] items-center gap-[7px] rounded-[6px] border-[1.5px] px-3 text-[13px] font-medium transition-colors duration-[120ms] ease-sarce ${
                  on ? "border-accent bg-accent-tint text-accent-text" : "border-transparent text-ink hover:bg-panel"
                }`}
              >
                <Icon name={item.id} size={16} />
                {item.label}
              </Link>
            );
          })}
        </nav>
        {account && <span className="ml-auto font-mono text-[11px] text-muted">{account}</span>}
        <span className={account ? "" : "ml-auto"}>
          <SettingsButton size={34} active={onSettings} />
        </span>
      </header>

      <header className="flex flex-none items-center gap-2 border-b border-line bg-surface px-[18px] pt-3 pb-[10px] md:hidden">
        <Link href="/" className="flex h-8 items-center gap-2 text-ink" aria-label="Sarce home">
          <SarceMark height={20} />
          <span className="text-[18px] font-medium tracking-[-0.02em]">sarce</span>
        </Link>
        <span className="font-mono text-[11px] text-muted">{title}</span>
        <span className="ml-auto">
          <SettingsButton size={36} active={onSettings} />
        </span>
      </header>

      <main className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-[1152px] flex-col md:max-w-[1184px] gap-3 px-4 pt-4 pb-7 md:gap-[18px] md:px-8 md:pt-7 md:pb-12">
          {children}
        </div>
      </main>

      <nav
        className="grid flex-none grid-cols-5 border-t border-line bg-surface px-[6px] pt-[6px] pb-[22px] md:hidden"
        aria-label="Main"
      >
        {NAV.map((item) => {
          const on = current === item.id;
          return (
            <Link
              key={item.id}
              href={item.href}
              aria-current={on ? "page" : undefined}
              className={`flex h-[50px] flex-col items-center justify-center gap-[3px] text-[10px] font-medium ${
                on ? "text-accent-text" : "text-muted"
              }`}
            >
              <Icon name={item.id} size={22} />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
