import { HomeView, type HomeData } from "@/components/home/home-view";
import { AppShell } from "@/components/shell/app-shell";

/*
 * Design preview: Home rendered with the v1.0 handoff's sample data, for side-by-side
 * comparison with the handoff screenshots. Not linked from the app; ?quiet=1 shows the
 * quiet-week variant.
 */

const SAMPLE: HomeData = {
  latest: {
    when: "2 min ago",
    meta: "1+0 · White · vs m_volkov · won",
    styleRead: "You set two real problems, and one sacrifice held.",
    chaos: [2, 3, 2, 5, 4, 3, 6, 4, 3, 5, 7, 4, 3, 6, 8, 5, 4, 7, 10, 6, 5, 4, 8, 6, 5, 3, 7, 4, 3, 2, 4, 3, 2, 2],
    highlight: 18,
    summaryHref: "/preview/home",
    reviewHref: "/preview/home",
    momentCount: 3,
  },
  brilliant: {
    window: "last 64",
    value: 4.1,
    spread: 1.2,
    trend: "↑ 0.6 this month",
    goalLo: 6,
    goalHi: 10,
    gapLine: "1.9 points below your 6–10% band, and closing.",
    streak: "6 games",
    soundRatio: "3.0 : 1",
    trapsSurvived: "62%",
  },
  doors: [
    { kicker: "Weekly recap · ready", accentKicker: true, title: "12 games, 4 that felt like you", action: "Pick next week's focus", href: "/preview/home" },
    { kicker: "Before your next game", title: "Today I want to: look for a sacrifice", action: "Change it in Play", href: "/preview/home" },
    { kicker: "Train · 7 waiting", title: "The sacrifice you didn't play", action: "vs ana_sicilia, move 21", href: "/preview/home" },
  ],
};

export default async function PreviewHome({ searchParams }: { searchParams: Promise<{ quiet?: string }> }) {
  const { quiet } = await searchParams;
  return (
    <AppShell title="home" account="kestrel_9 · Chess.com + Lichess · synced 2 min ago">
      <HomeView data={quiet ? { ...SAMPLE, quietUntil: "Oct 23" } : SAMPLE} />
    </AppShell>
  );
}
