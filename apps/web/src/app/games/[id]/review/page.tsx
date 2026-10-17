"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, use, useEffect, useState } from "react";
import { ReviewView } from "@/components/review/review-view";
import { AppShell } from "@/components/shell/app-shell";
import { PrimaryLink } from "@/components/ui/buttons";
import { Card } from "@/components/ui/card";
import { getGameReview, saveMoveIntent } from "@/lib/api";
import type { ReviewApi } from "@/types/chess";

function Review({ id }: { id: string }) {
  const ply = useSearchParams().get("ply");
  const [data, setData] = useState<ReviewApi | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    getGameReview(id).then(setData).catch(() => setFailed(true));
  }, [id]);

  return (
    <AppShell title={data?.opponent ? `review · ${data.opponent}` : "review"}>
      {data ? (
        <ReviewView
          data={data}
          initialPly={ply == null ? undefined : Number(ply)}
          onSaveIntent={(p, intent) => saveMoveIntent(id, p, intent)}
        />
      ) : failed ? (
        <Card className="items-start gap-3">
          <span className="text-[18px] font-medium">This review couldn&apos;t be loaded</span>
          <span className="text-[13px] leading-[1.55] text-ink-2">The game may be gone, or the analysis service is offline.</span>
          <PrimaryLink href="/">Back to Home</PrimaryLink>
        </Card>
      ) : (
        <div className="h-[2px] w-1/3 animate-pulse bg-accent" role="progressbar" aria-label="Loading" />
      )}
    </AppShell>
  );
}

export default function GameReviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return (
    <Suspense>
      <Review id={id} />
    </Suspense>
  );
}
