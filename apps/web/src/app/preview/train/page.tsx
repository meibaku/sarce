"use client";

import { AppShell } from "@/components/shell/app-shell";
import { TrainView } from "@/components/train/train-view";
import type { TrainApi } from "@/types/chess";

/* Design preview: the Train queue with the v1.0 handoff's sample drills. */

const FEN = "3q1rk1/4bppp/5n2/4R3/2B5/8/5PPP/3Q2K1 w - - 0 1";
const item = (n: number, source: string, meta: string, title: string, detail: string) => ({
  key: `preview-${n}`, source, meta, title, detail, fen: FEN, answer: "Nxf7", gameId: null, ply: null,
});

const SAMPLE: TrainApi = {
  band: 1600,
  waiting: 7,
  focus: "Keep setting real problems",
  items: [
    item(1, "find the sacrifice", "from your games", "The sacrifice you didn't play", "vs ana_sicilia, move 21. A sound Nxf7 was there."),
    item(2, "trap at your band", "trap atlas", "Survive …Qh4 in the Najdorf", "52% of 1600 bullet players fall for it."),
    item(3, "play the other side", "from your library", "Defend your own 19. Rxe5", "You're Black. Hold for 8 moves against Maia at 1600."),
    item(4, "guess the move", "reference game", "Tal – Fischer, 1959 · move 15", "In your Najdorf. Guess Tal's move, then read why."),
    item(5, "video position", "saved by you", "Tal's knight on e5", "Saved from video at 12:41 with your note."),
  ],
};

export default function PreviewTrain() {
  return (
    <AppShell title="train" account="kestrel_9 · Chess.com + Lichess · synced 2 min ago">
      <TrainView data={SAMPLE} onAnswer={async () => undefined} />
    </AppShell>
  );
}
