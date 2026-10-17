"use client";

import { useMemo, useState } from "react";
import { PrimaryLink, TextButton, TextLink } from "@/components/ui/buttons";
import { AutoGrid } from "@/components/ui/card";
import { MoveBadge } from "@/components/ui/move-badge";
import type { SacrificeRow } from "@/types/chess";

/*
 * Sacrifice library (handoff screen 6). A living record, newest first: every sacrifice is
 * "Held" or "Didn't hold" in grey, never a failure. The detail panel carries your note and
 * the one filled button, "Open in Review".
 */

type Filter = "all" | "held" | "not";

function date(iso: string | null) {
  return iso ? new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "";
}

/** A 1200×630 PNG of one sacrifice, drawn on a canvas and saved by the browser. */
function downloadShareCard(row: SacrificeRow) {
  const canvas = document.createElement("canvas");
  canvas.width = 1200;
  canvas.height = 630;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const css = getComputedStyle(document.documentElement);
  const v = (name: string) => css.getPropertyValue(name).trim();
  const sans = css.getPropertyValue("--font-plex-sans") || "sans-serif";
  const mono = css.getPropertyValue("--font-plex-mono") || "monospace";
  ctx.fillStyle = v("--page");
  ctx.fillRect(0, 0, 1200, 630);
  ctx.strokeStyle = v("--ink");
  ctx.lineWidth = 3;
  ctx.strokeRect(60, 60, 1080, 510);
  ctx.fillStyle = v("--muted");
  ctx.font = `500 28px ${mono}`;
  ctx.fillText(`vs ${row.opponent ?? "opponent"} · ${date(row.playedAt)}`, 110, 150);
  ctx.fillStyle = v("--ink");
  ctx.font = `500 96px ${mono}`;
  ctx.fillText(`${row.glyph}  ${row.label}`, 110, 290);
  ctx.font = `400 40px ${sans}`;
  ctx.fillText(`${row.type} −${row.material} · ${row.held ? "Held" : "Didn't hold"}`, 110, 370);
  if (row.note) {
    ctx.fillStyle = v("--ink-2");
    ctx.font = `400 30px ${sans}`;
    ctx.fillText(`“${row.note.slice(0, 70)}${row.note.length > 70 ? "…" : ""}”`, 110, 450);
  }
  ctx.fillStyle = v("--accent-text");
  ctx.font = `500 30px ${sans}`;
  ctx.fillText("sarce", 110, 530);
  const link = document.createElement("a");
  link.download = `sarce-${row.label.replace(/[^\w]+/g, "-")}.png`;
  link.href = canvas.toDataURL("image/png");
  link.click();
}

export function LibraryView({ rows }: { rows: SacrificeRow[] }) {
  const [filter, setFilter] = useState<Filter>("all");
  const shown = useMemo(
    () => rows.filter((r) => filter === "all" || (filter === "held" ? r.held : !r.held)),
    [rows, filter],
  );
  const [selected, setSelected] = useState(0);
  const sel = shown[Math.min(selected, shown.length - 1)];
  const chips: [Filter, string][] = [
    ["all", `All ${rows.length}`],
    ["held", "Held"],
    ["not", "Didn't hold"],
  ];

  return (
    <>
      <div className="flex flex-wrap items-baseline gap-3">
        <TextLink href="/you">← You</TextLink>
        <h1 className="text-[22px] font-medium">Your sacrifices</h1>
        <span className="font-mono text-[11px] text-muted">a living record · newest first</span>
      </div>
      <div className="flex flex-wrap gap-[6px]">
        {chips.map(([value, label]) => (
          <button
            key={value}
            type="button"
            aria-pressed={filter === value}
            onClick={() => {
              setFilter(value);
              setSelected(0);
            }}
            className={`h-8 rounded-[6px] border-[1.5px] px-3 text-[12px] font-medium ${
              filter === value ? "border-accent bg-accent-tint text-accent-text" : "border-line-2 bg-surface text-ink"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <AutoGrid min={380} className="items-start">
        <section className="overflow-hidden rounded-[8px] border border-line bg-surface">
          {shown.map((r, i) => (
            <button
              key={`${r.gameId}-${r.ply}`}
              type="button"
              onClick={() => setSelected(i)}
              aria-pressed={sel === r}
              className={`grid w-full grid-cols-[30px_minmax(0,1fr)_auto] items-center gap-3 border-t border-hair px-4 py-3 text-left first:border-t-0 ${
                sel === r ? "bg-accent-tint" : "bg-surface hover:bg-panel"
              }`}
            >
              <MoveBadge glyph={r.glyph} />
              <span className="flex min-w-0 flex-col gap-[2px]">
                <span className="font-mono text-[13px] font-medium">
                  {r.label}{" "}
                  <span className="font-sans font-normal text-muted">
                    · {r.type} −{r.material}
                  </span>
                </span>
                <span className="text-[12px] text-muted">
                  vs {r.opponent ?? "opponent"} · {date(r.playedAt)}
                </span>
              </span>
              <span className="text-[12px] text-ink-2">{r.held ? "Held" : "Didn't hold"}</span>
            </button>
          ))}
          {shown.length === 0 && <p className="px-4 py-6 text-[13px] text-muted">Nothing here with this filter.</p>}
        </section>

        {sel && (
          <section className="flex flex-col gap-[10px] rounded-[8px] border-[1.5px] border-ink bg-surface px-[18px] py-4">
            <div className="flex items-center gap-[10px]">
              <MoveBadge glyph={sel.glyph} size={28} />
              <span className="font-mono text-[16px] font-medium">{sel.label}</span>
              <span className="ml-auto font-mono text-[11px] text-muted">vs {sel.opponent ?? "opponent"}</span>
            </div>
            <span className="text-[13px] text-ink-2">
              {sel.held ? "Held · the engine found no refutation" : "Didn't hold · the engine found a way through"} · {sel.type} −{sel.material}
            </span>
            <div className="flex flex-col gap-[3px] rounded-[6px] bg-panel px-3 py-[10px]">
              <span className="font-mono text-[10px] text-muted">YOUR NOTE</span>
              <span className="text-[13px] leading-[1.45]">{sel.note || "No note yet. Add one in Review."}</span>
            </div>
            <div className="flex flex-wrap items-center gap-[18px]">
              <PrimaryLink href={`/games/${sel.gameId}/review?ply=${sel.ply}`} className="!h-10 !px-4">
                Open in Review
              </PrimaryLink>
              <TextLink href="/train">Defend it yourself</TextLink>
              <TextButton onClick={() => downloadShareCard(sel)}>Share card</TextButton>
            </div>
          </section>
        )}
      </AutoGrid>
    </>
  );
}
