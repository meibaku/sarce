"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { RecapView } from "@/components/recap/recap-view";
import { AppShell } from "@/components/shell/app-shell";
import { PrimaryLink } from "@/components/ui/buttons";
import { Card } from "@/components/ui/card";
import { getRecap, setFocus } from "@/lib/api";
import type { RecapApi } from "@/types/chess";

export default function RecapPage() {
  const router = useRouter();
  const [data, setData] = useState<RecapApi | null>(null);
  const [empty, setEmpty] = useState(false);

  useEffect(() => {
    getRecap().then(setData).catch(() => setEmpty(true));
  }, []);

  return (
    <AppShell title="weekly recap">
      {data ? (
        <RecapView
          data={data}
          onSetFocus={async (id) => {
            await setFocus("weekly", id);
            router.push("/train");
          }}
        />
      ) : empty ? (
        <Card className="items-start gap-3">
          <span className="text-[18px] font-medium">Your first recap comes after a few games</span>
          <span className="text-[13px] leading-[1.55] text-ink-2">Once games are analysed, each week gets a short recap and a focus.</span>
          <PrimaryLink href="/">Back to Home</PrimaryLink>
        </Card>
      ) : (
        <div className="h-[2px] w-1/3 animate-pulse bg-accent" role="progressbar" aria-label="Loading" />
      )}
    </AppShell>
  );
}
