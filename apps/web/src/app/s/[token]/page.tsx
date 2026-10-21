"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Board } from "@/components/ui/board";
import { Card, SectionLabel } from "@/components/ui/card";
import { SarceMark } from "@/components/ui/icons";
import { MoveBadge, type MoveGlyph } from "@/components/ui/move-badge";
import { StyleGauge } from "@/components/ui/style-gauge";
import { getPublicShare, type PublicShare } from "@/lib/api";

/*
 * A shared link (M8): the read-only snapshot someone shared from Sarce. No app shell, no sign-in, nothing
 * live: the page shows exactly what was stored when the link was made, and 404s once it is turned off.
 */

const RESULT = { win: "Won", loss: "Lost", draw: "Drew" } as const;

export default function SharedPage() {
  const { token } = useParams<{ token: string }>();
  const [data, setData] = useState<PublicShare | null>(null);
  const [gone, setGone] = useState(false);

  useEffect(() => {
    getPublicShare(token).then(setData).catch(() => setGone(true));
  }, [token]);

  return (
    <main className="mx-auto flex min-h-screen max-w-[720px] flex-col gap-4 px-4 py-8 md:px-6">
      <Link href="/" className="flex items-center gap-2 self-start">
        <SarceMark height={22} />
        <span className="text-[15px] font-semibold">sarce</span>
        <span className="font-mono text-[11px] text-muted">shared</span>
      </Link>

      {gone && (
        <Card className="gap-2 !p-[18px]">
          <span className="text-[18px] font-medium">This link isn&apos;t available</span>
          <span className="text-[13px] text-ink-2">It may have been turned off by the person who shared it.</span>
        </Card>
      )}
      {!data && !gone && <div className="h-[2px] w-1/3 animate-pulse bg-accent" role="progressbar" aria-label="Loading" />}

      {data?.kind === "summary" && (
        <>
          <span className="font-mono text-[11px] text-muted">
            {[data.result ? `${RESULT[data.result]} against an opponent` : "A game", data.timeControl].filter(Boolean).join(" · ")}
          </span>
          <h1 className="text-[24px] leading-[1.25] font-medium">{data.headline}</h1>
          {data.outcome && <p className="text-[14px] leading-[1.5] text-ink-2">{data.outcome}</p>}
          <Card className="gap-3 !p-[18px]">
            <SectionLabel>Brilliant this game · {data.brilliant.count ?? 0} of {data.brilliant.of ?? 0}</SectionLabel>
            <span className="font-mono text-[28px] text-accent-text">{(data.brilliant.pct ?? 0).toFixed(1)}%</span>
            <StyleGauge value={data.brilliant.pct ?? 0} goalLo={data.brilliant.goalLo ?? 6} goalHi={data.brilliant.goalHi ?? 10} />
          </Card>
          <Card className="gap-2 !p-[18px]">
            <SectionLabel>The moments</SectionLabel>
            {data.moments.map((m) => (
              <div key={m.label} className="flex items-center gap-3">
                <MoveBadge glyph={m.glyph as MoveGlyph} />
                <span className="font-mono text-[12px]">{m.label}</span>
                <span className="text-[13px] text-ink-2">{m.line}</span>
              </div>
            ))}
          </Card>
        </>
      )}

      {data?.kind === "sacrifice" && (
        <>
          <span className="font-mono text-[11px] text-muted">{["A sacrifice", data.opening, data.playedAt].filter(Boolean).join(" · ")}</span>
          <h1 className="text-[24px] font-medium">
            {data.label} · {data.type} −{data.material}
          </h1>
          <div className="w-full max-w-[420px]">
            <Board fen={data.fen} orientation={data.fen.split(" ")[1] === "b" ? "black" : "white"} label="The position before the sacrifice" />
          </div>
          <span className={`text-[14px] font-medium ${data.held ? "text-sound" : "text-muted"}`}>
            {data.held ? "It held: the engine found no refutation." : "It didn't hold: the engine found a way through."}
          </span>
        </>
      )}

      {data && (
        <span className="font-mono text-[11px] text-faint">
          Shared from Sarce, a chess style companion · a snapshot, not live · {new Date(data.sharedAt).toLocaleDateString()}
        </span>
      )}
    </main>
  );
}
