"use client";

import { useEffect, useState } from "react";
import { TextButton } from "@/components/ui/buttons";
import { SectionLabel } from "@/components/ui/card";
import { listShares, revokeShare, type SharedLink } from "@/lib/api";

/* Settings → Shared links: every page you shared, with its address and a way to turn it off. */

export function SharedLinks() {
  const [links, setLinks] = useState<SharedLink[] | null>(null);
  useEffect(() => {
    listShares()
      .then((r) => setLinks(r.links))
      .catch(() => setLinks([]));
  }, []);
  const live = (links ?? []).filter((l) => !l.revoked_at);

  return (
    <section className="flex flex-col gap-[10px] rounded-[8px] border border-line bg-surface p-[18px]">
      <SectionLabel>Shared links</SectionLabel>
      {links && live.length === 0 && <span className="text-[13px] text-muted">Nothing shared. Summary and the library have &quot;Share link&quot;.</span>}
      {live.map((l) => (
        <div key={l.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-hair pt-2 first-of-type:border-t-0">
          <span className="text-[13px]">{l.kind === "summary" ? l.snapshot.headline ?? "A game summary" : `Sacrifice ${l.snapshot.label ?? ""}`}</span>
          <a href={`/s/${l.token}`} target="_blank" rel="noopener" className="font-mono text-[11px] text-accent-text">
            /s/{l.token.slice(0, 8)}…
          </a>
          <span className="flex-1" />
          <TextButton
            className="!text-muted"
            onClick={() => revokeShare(l.id).then(() => setLinks((all) => (all ?? []).map((x) => (x.id === l.id ? { ...x, revoked_at: new Date().toISOString() } : x))))}
          >
            Turn off
          </TextButton>
        </div>
      ))}
    </section>
  );
}
