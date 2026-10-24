"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Card, SectionLabel } from "@/components/ui/card";
import { SarceMark } from "@/components/ui/icons";
import { MoveBadge } from "@/components/ui/move-badge";
import { getBrilliantDefinition, type BrilliantDefinition } from "@/lib/api";

/*
 * What "Brilliant" means in Sarce (plan 3.3): public, no sign-in. The clauses and their numbers come from the API
 * (services/brilliant.definition), so this page always says what the rule actually does. Chess.com's Brilliant is
 * a different definition; where they disagree, Review says which clause made the difference.
 */
export default function BrilliantPage() {
  const [data, setData] = useState<BrilliantDefinition | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    getBrilliantDefinition().then(setData).catch(() => setFailed(true));
  }, []);

  return (
    <main className="mx-auto flex min-h-screen max-w-[720px] flex-col gap-4 px-4 py-8 md:px-6">
      <Link href="/" className="flex items-center gap-2 self-start">
        <SarceMark height={22} />
        <span className="text-[15px] font-semibold">sarce</span>
      </Link>
      <div className="flex items-center gap-3">
        <MoveBadge glyph="!!" />
        <h1 className="text-[22px] font-medium">What Sarce calls Brilliant</h1>
      </div>
      <p className="text-[14px] leading-[1.6] text-ink-2">
        A Brilliant move is a sound sacrifice that players at your level rarely find. Every condition below has to hold. It is a
        stricter idea than most sites&apos; Brilliant, so the two will sometimes disagree; when a sacrifice misses by one
        condition, Review calls it &ldquo;almost Brilliant&rdquo; and names it.
      </p>
      {failed && <p className="text-[13px] text-muted">The definition couldn&apos;t be loaded. Try again in a moment.</p>}
      {data && (
        <Card className="gap-0 !p-0">
          {data.clauses.map((c, i) => (
            <div key={c.id} className={`flex gap-3 px-[18px] py-[14px] ${i ? "border-t border-hair" : ""}`}>
              <span className="font-mono text-[12px] text-muted">{i + 1}</span>
              <div className="flex flex-col gap-1">
                <span className="text-[15px] font-medium">{c.title}</span>
                <span className="text-[13px] leading-[1.55] text-ink-2">{c.text}</span>
              </div>
            </div>
          ))}
        </Card>
      )}
      {data && (
        <div className="flex flex-col gap-1">
          <SectionLabel>Expected points</SectionLabel>
          <p className="text-[13px] leading-[1.55] text-ink-2">
            Expected points are your chances in the game: 1 for a win, 0.5 for a draw, 0 for a loss. Measuring in them means a
            quarter-pawn counts for a lot in a level game and for little when the game is already decided. Rule {data.rule}.
          </p>
        </div>
      )}
    </main>
  );
}
