"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { RecapView } from "@/components/recap/recap-view";
import { AppShell } from "@/components/shell/app-shell";
import { EdgeState } from "@/components/ui/edge-state";
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
        <EdgeState kind="too-few" detail="Once games are analysed, each week gets a short recap and a focus." action="Back to Home" href="/" />
      ) : (
        <div className="h-[2px] w-1/3 animate-pulse bg-accent" role="progressbar" aria-label="Loading" />
      )}
    </AppShell>
  );
}
