"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/shell/app-shell";
import { EdgeState } from "@/components/ui/edge-state";
import { getHome } from "@/lib/api";

/** The Review tab opens the latest analysed game. */
export default function ReviewIndex() {
  const router = useRouter();
  const [empty, setEmpty] = useState(false);

  useEffect(() => {
    getHome()
      .then((home) => (home.latest ? router.replace(`/games/${home.latest.gameId}/review`) : setEmpty(true)))
      .catch(() => setEmpty(true));
  }, [router]);

  return (
    <AppShell title="review">
      {empty ? (
        <EdgeState kind="no-games" detail="Once a game is analysed, its moments open here." href="/onboarding" />
      ) : (
        <div className="h-[2px] w-1/3 animate-pulse bg-accent" role="progressbar" aria-label="Loading" />
      )}
    </AppShell>
  );
}
