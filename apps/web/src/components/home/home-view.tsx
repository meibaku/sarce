import Link from "next/link";
import { PrimaryLink, TextLink } from "@/components/ui/buttons";
import { AutoGrid, Card, SectionLabel, Stat } from "@/components/ui/card";
import { ChaosStrip } from "@/components/ui/chaos-strip";
import { SarceMark } from "@/components/ui/icons";
import { StyleGauge } from "@/components/ui/style-gauge";

/*
 * Home (handoff screen 2). The latest-game card leads with the style read sentence; the
 * result is metadata only. The Brilliant card holds the screen's only big number. This view
 * is presentational: data loading lives in the page so the same markup serves real data,
 * the quiet week and the preview.
 */

export interface HomeData {
  latest: {
    when: string;
    meta: string;
    styleRead: string;
    chaos: number[];
    highlight: number | null;
    summaryHref: string;
    reviewHref: string;
    momentCount: number;
  };
  brilliant: {
    window: string;
    value: number;
    spread?: number;
    trend?: string;
    goalLo: number;
    goalHi: number;
    gapLine: string;
    streak: string;
    soundRatio: string;
    trapsSurvived: string;
  };
  doors: { kicker: string; accentKicker?: boolean; title: string; action: string; href: string }[];
  quietUntil?: string;
}

function DoorTile({ door }: { door: HomeData["doors"][number] }) {
  return (
    <Link
      href={door.href}
      className="flex flex-col gap-[6px] rounded-[8px] border border-line bg-surface px-[18px] py-4 text-left transition-colors duration-[120ms] ease-sarce hover:border-ink"
    >
      <span className={`font-mono text-[11px] ${door.accentKicker ? "text-accent-text" : "text-muted"}`}>{door.kicker}</span>
      <span className="text-[15px] font-medium">{door.title}</span>
      <span className="text-[13px] text-muted">{door.action} →</span>
    </Link>
  );
}

export function HomeView({ data }: { data: HomeData }) {
  const { latest, brilliant, doors, quietUntil } = data;
  const quiet = Boolean(quietUntil);

  return (
    <>
      {quiet && (
        <div className="flex flex-wrap items-center gap-3 rounded-[8px] border-[1.5px] border-dashed border-line-3 px-4 py-3">
          <span className="flex-[1_1_220px] text-[13px] text-ink-2">
            Quiet week until {quietUntil} · numbers are hidden, moments and notes stay.
          </span>
          <TextLink href="/settings">End early</TextLink>
        </div>
      )}

      <AutoGrid min={380}>
        <Card lead className="gap-[14px]">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-[6px] font-mono text-[11px] text-muted">
            <span>Latest game · {latest.when}</span>
            <span className="order-9 -mt-[10px] -mb-2 ml-auto text-ink">
              <SarceMark height={44} framed />
            </span>
            <span className="rounded-[5px] border border-line-2 px-[7px] py-px">{latest.meta}</span>
          </div>
          <span className="text-[22px] leading-[1.3] font-medium text-pretty">{latest.styleRead}</span>
          <ChaosStrip values={latest.chaos} highlight={latest.highlight} />
          <div className="flex flex-wrap items-center gap-[18px]">
            <PrimaryLink href={latest.summaryHref}>
              See the {latest.momentCount} moment{latest.momentCount === 1 ? "" : "s"}
            </PrimaryLink>
            <TextLink href={latest.reviewHref}>Full review</TextLink>
          </div>
        </Card>

        <Card className="gap-3">
          <div className="flex flex-wrap items-baseline gap-[10px]">
            <SectionLabel>Brilliant · {brilliant.window}</SectionLabel>
            {quiet ? (
              <span className="font-mono text-[20px] text-faint">hidden this week</span>
            ) : (
              <>
                <span className="font-mono text-[32px] text-accent-text">{brilliant.value.toFixed(1)}%</span>
                {(brilliant.spread != null || brilliant.trend) && (
                  <span className="font-mono text-[12px] text-faint">
                    {[brilliant.spread != null ? `±${brilliant.spread.toFixed(1)}` : null, brilliant.trend]
                      .filter(Boolean)
                      .join(" · ")}
                  </span>
                )}
              </>
            )}
          </div>
          {!quiet && (
            <>
              <StyleGauge
                value={brilliant.value}
                goalLo={brilliant.goalLo}
                goalHi={brilliant.goalHi}
                spread={brilliant.spread}
              />
              <span className="text-[13px] leading-[1.5] text-muted">{brilliant.gapLine}</span>
              <div className="flex flex-wrap gap-5 border-t border-hair pt-[10px]">
                <Stat label="style streak" value={brilliant.streak} />
                <Stat label="sound : unsound" value={brilliant.soundRatio} />
                <Stat label="traps survived" value={brilliant.trapsSurvived} />
              </div>
            </>
          )}
        </Card>
      </AutoGrid>

      <AutoGrid min={300}>
        {doors.map((door) => (
          <DoorTile key={door.title} door={door} />
        ))}
      </AutoGrid>
    </>
  );
}
