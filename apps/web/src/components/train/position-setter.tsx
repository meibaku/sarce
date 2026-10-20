"use client";

import { useState } from "react";
import { PrimaryButton, TextButton } from "@/components/ui/buttons";
import { Board } from "@/components/ui/board";
import { SectionLabel } from "@/components/ui/card";
import { showToast } from "@/components/ui/toast";
import { savePosition } from "@/lib/api";

/*
 * Manual position setter (PHASES 2.1): paste a FEN from a video, a book or an analysis board and keep
 * it as a Train drill ("a saved position"). The board previews the placement as you type; the API
 * checks the position is legal and playable before saving.
 */

const PLACEMENT = /^([rnbqkpRNBQKP1-8]+\/){7}[rnbqkpRNBQKP1-8]+$/;

export function PositionSetter({ onSaved }: { onSaved?: () => void }) {
  const [open, setOpen] = useState(false);
  const [fen, setFen] = useState("");
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const placement = fen.trim().split(/\s+/)[0] ?? "";
  const previewable = PLACEMENT.test(placement);
  const field = "h-10 rounded-[6px] border-[1.5px] border-line-2 bg-surface px-3 text-[13px] placeholder:text-faint";

  if (!open) {
    return (
      <TextButton className="self-start" onClick={() => setOpen(true)}>
        Save a position from a video or book
      </TextButton>
    );
  }

  return (
    <section className="flex flex-col gap-3 rounded-[8px] border border-line bg-surface p-[18px]">
      <SectionLabel>Save a position</SectionLabel>
      <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_200px]">
        <div className="flex flex-col gap-2">
          <input
            value={fen}
            onChange={(e) => setFen(e.target.value)}
            placeholder="FEN, e.g. from Lichess: Share & export → FEN"
            aria-label="Position (FEN)"
            spellCheck={false}
            className={`${field} font-mono`}
          />
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title (optional)" aria-label="Title" maxLength={80} className={field} />
          <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="What to look for (optional)" aria-label="Note" maxLength={300} className={field} />
          {error && <span className="text-[12px] text-muted">{error}</span>}
          <div className="flex items-center gap-[18px]">
            <PrimaryButton
              disabled={!previewable}
              className="!px-5"
              onClick={() =>
                savePosition({ fen: fen.trim(), title: title.trim() || undefined, note: note.trim() || undefined })
                  .then(() => {
                    showToast("Saved. It comes up in your queue.", "nod");
                    setFen("");
                    setTitle("");
                    setNote("");
                    setError(null);
                    setOpen(false);
                    onSaved?.();
                  })
                  .catch(() => setError("That isn't a playable position. Check the FEN, including whose move it is."))
              }
            >
              Save to Train
            </PrimaryButton>
            <TextButton className="!text-muted" onClick={() => setOpen(false)}>
              Cancel
            </TextButton>
          </div>
        </div>
        <div className="w-[200px]">
          {previewable ? (
            <Board compact fen={`${placement} w - - 0 1`} label="Preview of the pasted position" />
          ) : (
            <div className="grid aspect-square place-items-center rounded-[4px] border border-dashed border-line-3 text-[12px] text-faint">preview</div>
          )}
        </div>
      </div>
    </section>
  );
}
