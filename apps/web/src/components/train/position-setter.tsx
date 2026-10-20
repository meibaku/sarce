"use client";

import { useState } from "react";
import { PrimaryButton, TextButton } from "@/components/ui/buttons";
import { Board } from "@/components/ui/board";
import { SectionLabel } from "@/components/ui/card";
import { showToast } from "@/components/ui/toast";
import { fenFromImage, savePosition, summarizeExcerpt, videoExcerpt } from "@/lib/api";

/*
 * Save a position into Train (PHASES 2.1-2.4). Three ways in:
 * - FEN: paste it (from Lichess, a book, an analysis board);
 * - Screenshot: Claude reads the board (opt-in, sent to AI) and the FEN comes back checked;
 * - Video: a YouTube link at the moment; Sarce keeps the transcript around it (captions, no AI) and,
 *   if you opted in, a short AI summary of what was said.
 * The board previews the placement; the API checks the position is legal and playable before saving.
 */

const PLACEMENT = /^([rnbqkpRNBQKP1-8]+\/){7}[rnbqkpRNBQKP1-8]+$/;
type Mode = "fen" | "image" | "video";

function readAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1] ?? "");
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

export function PositionSetter({ aiHelp = false, onSaved }: { aiHelp?: boolean; onSaved?: () => void }) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<Mode>("fen");
  const [fen, setFen] = useState("");
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [video, setVideo] = useState("");
  const [pasted, setPasted] = useState("");
  const [needPaste, setNeedPaste] = useState(false);
  const [excerpt, setExcerpt] = useState<{ text: string; at: number } | null>(null);
  const [summary, setSummary] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const placement = fen.trim().split(/\s+/)[0] ?? "";
  const previewable = PLACEMENT.test(placement);
  const field = "h-10 rounded-[6px] border-[1.5px] border-line-2 bg-surface px-3 text-[13px] placeholder:text-faint";
  const tab = (on: boolean) =>
    `h-8 rounded-[6px] border-[1.5px] px-3 text-[12px] font-medium ${on ? "border-accent bg-accent-tint text-accent-text" : "border-line-2 bg-surface text-ink"}`;

  function reset() {
    setFen("");
    setTitle("");
    setNote("");
    setVideo("");
    setPasted("");
    setNeedPaste(false);
    setExcerpt(null);
    setSummary("");
    setError(null);
  }

  async function readScreenshot(file: File) {
    setBusy("Reading the board…");
    setError(null);
    try {
      const out = await fenFromImage(await readAsBase64(file), file.type);
      setFen(out.fen);
      if (out.notes) setNote(out.notes);
      showToast(out.confidence === "high" ? "Board read. Check it before saving." : "Board read, but check every square.", "think");
    } catch (e) {
      setError(e instanceof Error && e.message.includes("403") ? "Turn on Settings → Video help (sent to AI) to read screenshots." : "The board couldn't be read. Try a clearer screenshot, or paste the FEN.");
    } finally {
      setBusy(null);
    }
  }

  async function fetchExcerpt() {
    setBusy("Reading the captions…");
    setError(null);
    try {
      const out = await videoExcerpt(video.trim(), needPaste ? pasted : undefined);
      setExcerpt({ text: out.text, at: out.at });
      if (!out.text) setError("No captions near that moment. Check the time in the link.");
    } catch (e) {
      const blocked = e instanceof Error && e.message.includes("503");
      setNeedPaste(blocked);
      setError(blocked ? "YouTube is blocking caption requests from this network. Paste the transcript below (… → Show transcript on YouTube)." : "Couldn't read captions for that link.");
    } finally {
      setBusy(null);
    }
  }

  async function summarize() {
    if (!excerpt) return;
    setBusy("Summarising…");
    try {
      const out = await summarizeExcerpt(excerpt.text, previewable ? fen.trim() : undefined);
      setSummary([out.summary, ...out.ideas.map((i) => `• ${i}`)].join("\n"));
      if (!title) setTitle(out.title);
    } catch {
      setError("The summary couldn't be made. The transcript is still saved with the position.");
    } finally {
      setBusy(null);
    }
  }

  if (!open) {
    return (
      <TextButton className="self-start" onClick={() => setOpen(true)}>
        Save a position from a video, screenshot or book
      </TextButton>
    );
  }

  return (
    <section className="flex flex-col gap-3 rounded-[8px] border border-line bg-surface p-[18px]">
      <div className="flex flex-wrap items-center gap-[6px]">
        <SectionLabel>Save a position</SectionLabel>
        <span className="flex-1" />
        {(
          [
            ["fen", "FEN"],
            ["image", "Screenshot"],
            ["video", "Video"],
          ] as [Mode, string][]
        ).map(([m, label]) => (
          <button key={m} type="button" aria-pressed={mode === m} onClick={() => setMode(m)} className={tab(mode === m)}>
            {label}
          </button>
        ))}
      </div>
      <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_200px]">
        <div className="flex flex-col gap-2">
          {mode === "image" && (
            <label className="flex flex-col gap-1 text-[12px] text-muted">
              {aiHelp ? "A screenshot of the board (sent to Claude to read it)" : "Reading screenshots needs Settings → Video help (sent to AI)."}
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                disabled={!aiHelp || Boolean(busy)}
                onChange={(e) => e.target.files?.[0] && readScreenshot(e.target.files[0])}
                className="text-[13px] text-ink"
              />
            </label>
          )}
          {mode === "video" && (
            <>
              <div className="flex gap-2">
                <input
                  value={video}
                  onChange={(e) => setVideo(e.target.value)}
                  placeholder="YouTube link at the moment (Share → Start at)"
                  aria-label="YouTube link"
                  className={`${field} flex-1`}
                />
                <TextButton disabled={!video.trim() || Boolean(busy)} onClick={fetchExcerpt}>
                  Get what was said
                </TextButton>
              </div>
              {needPaste && (
                <textarea
                  value={pasted}
                  onChange={(e) => setPasted(e.target.value)}
                  placeholder="Paste the transcript (with its timestamps) or just the part you want"
                  aria-label="Pasted transcript"
                  className="min-h-20 rounded-[6px] border-[1.5px] border-line-2 bg-surface px-3 py-2 text-[12px] placeholder:text-faint"
                />
              )}
              {excerpt?.text && (
                <div className="flex flex-col gap-1 rounded-[6px] bg-panel p-3">
                  <span className="font-mono text-[10px] text-muted">WHAT WAS SAID · around {Math.floor(excerpt.at / 60)}:{String(excerpt.at % 60).padStart(2, "0")}</span>
                  <span className="max-h-28 overflow-auto text-[12px] leading-[1.5] text-ink-2">{excerpt.text}</span>
                  {aiHelp ? (
                    <TextButton className="self-start" disabled={Boolean(busy)} onClick={summarize}>
                      Summarise with AI
                    </TextButton>
                  ) : (
                    <span className="text-[11px] text-muted">Turn on Settings → Video help to get a short AI summary.</span>
                  )}
                  {summary && <span className="whitespace-pre-line text-[12px] leading-[1.5] text-ink">{summary}</span>}
                </div>
              )}
            </>
          )}
          <input
            value={fen}
            onChange={(e) => setFen(e.target.value)}
            placeholder={mode === "fen" ? "FEN, e.g. from Lichess: Share & export → FEN" : "The position (FEN): read from the screenshot, or paste it"}
            aria-label="Position (FEN)"
            spellCheck={false}
            className={`${field} font-mono`}
          />
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title (optional)" aria-label="Title" maxLength={80} className={field} />
          <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="What to look for (optional)" aria-label="Note" maxLength={300} className={field} />
          {busy && <span className="font-mono text-[11px] text-muted">{busy}</span>}
          {error && <span className="text-[12px] text-muted">{error}</span>}
          <div className="flex items-center gap-[18px]">
            <PrimaryButton
              disabled={!previewable || Boolean(busy)}
              className="!px-5"
              onClick={() =>
                savePosition({
                  fen: fen.trim(),
                  title: title.trim() || undefined,
                  note: note.trim() || undefined,
                  sourceUrl: mode === "video" && video.trim() ? video.trim() : undefined,
                  sourceTimeS: mode === "video" ? excerpt?.at : undefined,
                  excerpt: mode === "video" ? excerpt?.text || undefined : undefined,
                  aiSummary: summary || undefined,
                })
                  .then(() => {
                    showToast("Saved. It comes up in your queue.", "nod");
                    reset();
                    setOpen(false);
                    onSaved?.();
                  })
                  .catch(() => setError("That isn't a playable position. Check the FEN, including whose move it is."))
              }
            >
              Save to Train
            </PrimaryButton>
            <TextButton
              className="!text-muted"
              onClick={() => {
                reset();
                setOpen(false);
              }}
            >
              Cancel
            </TextButton>
          </div>
        </div>
        <div className="w-[200px]">
          {previewable ? (
            <Board compact fen={`${placement} w - - 0 1`} label="Preview of the position" />
          ) : (
            <div className="grid aspect-square place-items-center rounded-[4px] border border-dashed border-line-3 text-[12px] text-faint">preview</div>
          )}
        </div>
      </div>
    </section>
  );
}
