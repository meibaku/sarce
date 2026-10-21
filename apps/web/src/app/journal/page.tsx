"use client";

import { useEffect, useState } from "react";
import { SarceMark } from "@/components/ui/icons";
import { getJournalText } from "@/lib/api";

/*
 * The journal as a printable page (Settings → Export journal (PDF)). The API's Markdown is a small,
 * known shape (# title, ## sections, "- " entries, "  - " notes), so it is rendered here directly;
 * with ?print=1 the print dialog opens once it has loaded, where "Save as PDF" makes the file.
 */

type Block = { kind: "h1" | "h2" | "p" | "item" | "note"; text: string };

function parse(md: string): Block[] {
  return md
    .split("\n")
    .filter((line) => line.trim())
    .map((line) =>
      line.startsWith("# ")
        ? { kind: "h1", text: line.slice(2) }
        : line.startsWith("## ")
          ? { kind: "h2", text: line.slice(3) }
          : line.startsWith("  - ")
            ? { kind: "note", text: line.slice(4) }
            : line.startsWith("- ")
              ? { kind: "item", text: line.slice(2) }
              : { kind: "p", text: line },
    );
}

export default function JournalPage() {
  const [blocks, setBlocks] = useState<Block[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    getJournalText()
      .then((md) => {
        setBlocks(parse(md));
        if (new URLSearchParams(window.location.search).get("print")) setTimeout(() => window.print(), 300);
      })
      .catch(() => setFailed(true));
  }, []);

  return (
    <main className="mx-auto flex max-w-[720px] flex-col gap-2 px-6 py-10 print:px-0 print:py-0">
      <div className="mb-4 flex items-center gap-2 print:mb-2">
        <SarceMark height={20} />
        <span className="font-mono text-[11px] text-muted">sarce · journal</span>
        <button
          type="button"
          onClick={() => window.print()}
          className="ml-auto h-9 rounded-[6px] border-[1.5px] border-ink bg-surface px-[14px] text-[12px] font-medium print:hidden"
        >
          Save as PDF
        </button>
      </div>
      {failed && <p className="text-[13px] text-ink-2">The journal couldn&apos;t be loaded. Is the analysis service running?</p>}
      {!blocks && !failed && <div className="h-[2px] w-1/3 animate-pulse bg-accent" role="progressbar" aria-label="Loading" />}
      {blocks?.map((b, i) =>
        b.kind === "h1" ? (
          <h1 key={i} className="text-[24px] font-medium">{b.text}</h1>
        ) : b.kind === "h2" ? (
          <h2 key={i} className="mt-5 border-b border-line pb-1 text-[16px] font-medium break-after-avoid">{b.text}</h2>
        ) : b.kind === "item" ? (
          <p key={i} className="font-mono text-[12px] leading-[1.6] text-ink break-inside-avoid">{b.text}</p>
        ) : b.kind === "note" ? (
          <p key={i} className="ml-4 border-l-2 border-line pl-3 text-[13px] leading-[1.5] text-ink-2 break-inside-avoid">{b.text}</p>
        ) : (
          <p key={i} className="text-[13px] leading-[1.5] text-ink-2">{b.text}</p>
        ),
      )}
    </main>
  );
}
