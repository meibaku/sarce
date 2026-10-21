"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, use, useEffect, useState } from "react";
import { ReviewView } from "@/components/review/review-view";
import { AppShell } from "@/components/shell/app-shell";
import { EdgeState } from "@/components/ui/edge-state";
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
        <EdgeState kind="failed" detail="This review couldn't be loaded. The game may be gone, or the analysis service is offline." action="Back to Home" href="/" />
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
