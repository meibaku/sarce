import Link from "next/link";
import type { GameListItem } from "@/lib/api";

function titleCase(value: string) {
  return value[0].toUpperCase() + value.slice(1);
}

function gameState(game: GameListItem) {
  if (game.pilotResonance) return { label: `Answered · ${titleCase(game.pilotResonance)}`, tone: "quiet" };
  if (game.analysisStatus === "complete") return { label: "Ready for your answer", tone: "action" };
  if (game.analysisStatus === "failed") return { label: "Read unavailable", tone: "quiet" };
  if (game.analysisStatus === "processing") return { label: game.analysisProgress == null ? "Reading game" : `Reading · ${Math.round(game.analysisProgress)}%`, tone: "quiet" };
  return { label: "Waiting", tone: "quiet" };
}

function gameSummary(game: GameListItem) {
  if (game.analysisStatus === "failed") return "The game is safe, but its style read did not finish.";
  if (game.analysisStatus !== "complete") return "Sarce is preparing this finished game.";
  return game.pilotResonance ? "Your saved style read is available." : "Your style read is ready to review.";
}

export function PilotGameRow({ game }: { game: GameListItem }) {
  const state = gameState(game);
  const result = game.result === "win" ? "You won" : game.result === "loss" ? "You lost" : game.result === "draw" ? "Draw" : "Finished";
  const date = game.playedAt ? new Date(game.playedAt).toLocaleDateString() : null;
  const details = [date, game.timeControl, game.userColor ? `You played ${game.userColor}` : null, game.totalMoves ? `${game.totalMoves} moves` : null].filter(Boolean);
  const readable = game.analysisStatus === "complete";

  return (
    <article className={`grid gap-4 px-4 py-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center ${state.tone === "action" ? "border-l-[3px] border-l-accent bg-accent-tint" : "border-l-[3px] border-l-transparent"}`}>
      <div className="min-w-0">
        <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted">Opponent</p>
        <h3 className="mt-1 truncate text-[16px] font-semibold">{game.opponent ?? "Unknown opponent"}</h3>
        <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12px] text-muted">
          <span className="font-medium text-ink-2">{result}</span>
          {details.map((detail) => <span key={detail} className="before:mr-2 before:text-line-3 before:content-['·']">{detail}</span>)}
        </div>
        <p className="mt-2 text-[13px] leading-5 text-ink-2">{gameSummary(game)}</p>
      </div>
      <div className="flex min-w-[170px] items-center justify-between gap-3 sm:flex-col sm:items-end">
        <div className="sm:text-right"><span className="block font-mono text-[9px] uppercase tracking-[0.1em] text-muted">Status</span><span className={`mt-1 inline-flex min-h-7 items-center rounded-full border px-3 font-mono text-[11px] ${state.tone === "action" ? "border-accent bg-surface text-accent-text" : "border-line-2 bg-panel text-ink-2"}`}>{state.label}</span></div>
        {readable && <Link href={`/games/${game.id}`} className="inline-flex min-h-11 items-center font-medium text-accent-text underline underline-offset-4">{game.pilotResonance ? "Open saved read" : "Open style read"} →</Link>}
        {game.analysisStatus === "failed" && game.externalUrl && <a href={game.externalUrl} target="_blank" rel="noreferrer" className="inline-flex min-h-11 items-center text-accent-text underline underline-offset-4">Open source game ↗</a>}
      </div>
    </article>
  );
}
