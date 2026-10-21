"use client";

import { useEffect, useState } from "react";
import { TextButton } from "@/components/ui/buttons";
import { SectionLabel } from "@/components/ui/card";
import { deletePosition, listPositions } from "@/lib/api";
import type { SavedPosition } from "@/types/chess";

/*
 * The searchable position library (PHASES 2 goal): everything you saved from games, books and videos.
 * Search matches every word against titles, notes, transcript excerpts and summaries (server side).
 */

export function SavedPositions({ refresh = 0 }: { refresh?: number }) {
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<SavedPosition[] | null>(null);

  useEffect(() => {
    const id = setTimeout(() => {
      listPositions(q.trim() || undefined)
        .then((r) => setRows(r.positions))
        .catch(() => setRows([]));
    }, 250);
    return () => clearTimeout(id);
  }, [q, refresh]);

  if (rows && rows.length === 0 && !q) return null;
  return (
    <section className="flex flex-col gap-2 rounded-[8px] border border-line bg-surface p-[18px]">
      <div className="flex flex-wrap items-center gap-3">
        <SectionLabel>Your positions</SectionLabel>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search titles, notes and what was said"
          aria-label="Search saved positions"
          className="h-8 min-w-[220px] flex-1 rounded-[6px] border-[1.5px] border-line-2 bg-surface px-3 text-[12px] placeholder:text-faint"
        />
      </div>
      {rows?.length === 0 && <span className="text-[12px] text-muted">Nothing matches.</span>}
      {rows?.map((p) => (
        <div key={p.id} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-t border-hair pt-2 first-of-type:border-t-0">
          <span className="text-[13px] font-medium">{p.title}</span>
          <span className="font-mono text-[10px] text-muted">{p.source_url ? "from a video" : p.game_id ? "from your game" : "saved"}</span>
          {p.source_url && (
            <a
              href={`${p.source_url}${p.source_time_s != null && !p.source_url.includes("t=") ? `${p.source_url.includes("?") ? "&" : "?"}t=${p.source_time_s}` : ""}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[12px] font-medium text-accent-text"
            >
              Watch ↗
            </a>
          )}
          <span className="flex-1" />
          <TextButton
            className="!text-muted"
            onClick={() => deletePosition(p.id).then(() => setRows((r) => (r ?? []).filter((x) => x.id !== p.id)))}
          >
            Remove
          </TextButton>
          {(p.ai_summary || p.note || p.excerpt) && (
            <span className="basis-full text-[12px] leading-[1.45] text-ink-2 line-clamp-2">{p.ai_summary || p.note || p.excerpt}</span>
          )}
        </div>
      ))}
    </section>
  );
}
