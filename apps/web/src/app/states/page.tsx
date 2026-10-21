"use client";

import { useState } from "react";
import { AppShell } from "@/components/shell/app-shell";
import { AutoGrid } from "@/components/ui/card";
import { EDGE, EdgeState, type EdgeKind } from "@/components/ui/edge-state";

/* Settings → Preview edge states: every empty, waiting and error state the screens can show. */
export default function StatesPage() {
  const kinds = Object.keys(EDGE) as EdgeKind[];
  const [kind, setKind] = useState<EdgeKind>("no-games");
  return (
    <AppShell title="states">
      <h1 className="text-[22px] font-medium">Edge states</h1>
      <AutoGrid min={300} className="items-start">
        <section className="overflow-hidden rounded-[8px] border border-line bg-surface">
          {kinds.map((k) => (
            <button
              key={k}
              type="button"
              aria-pressed={k === kind}
              onClick={() => setKind(k)}
              className={`w-full border-t border-hair px-4 py-3 text-left text-[13px] font-medium first:border-t-0 ${k === kind ? "bg-accent-tint" : "bg-surface hover:bg-panel"}`}
            >
              {EDGE[k].title}
            </button>
          ))}
        </section>
        <EdgeState kind={kind} onAction={() => undefined} />
      </AutoGrid>
    </AppShell>
  );
}
