"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/shell/app-shell";
import { PrimaryLink } from "@/components/ui/buttons";
import { Card } from "@/components/ui/card";
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
        <Card className="items-start gap-3">
          <span className="text-[18px] font-medium">Nothing to review yet</span>
          <span className="text-[13px] leading-[1.55] text-ink-2">Once a game is analysed, its moments open here.</span>
          <PrimaryLink href="/">Back to Home</PrimaryLink>
        </Card>
      ) : (
        <div className="h-[2px] w-1/3 animate-pulse bg-accent" role="progressbar" aria-label="Loading" />
      )}
    </AppShell>
  );
}
