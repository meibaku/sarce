import type { ImportJobStatus } from "@/types/chess";

interface ImportProgressProps {
  job: ImportJobStatus;
  analyzing?: boolean;
}

export function ImportProgress({ job, analyzing = false }: ImportProgressProps) {
  const isActive = job.status === "queued" || job.status === "running";
  const failed = job.status === "failed";

  return (
    <div className="rounded-lg border border-white/10 bg-surface px-4 py-3">
      <div className="flex items-center justify-between gap-4 text-sm">
        <p className={failed ? "text-red-300" : "text-foreground/80"}>
          {job.message}
          {analyzing && " Analyzing new games with Stockfish..."}
        </p>
        {isActive && (
          <span className="tabular-nums text-foreground/50">
            {job.progressPct.toFixed(0)}%
          </span>
        )}
      </div>

      {isActive && (
        <div className="mt-3 h-2 overflow-hidden rounded-full bg-background">
          <div
            className="h-full rounded-full bg-accent transition-all duration-500"
            style={{ width: `${Math.max(job.progressPct, job.status === "queued" ? 4 : 0)}%` }}
          />
        </div>
      )}

      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-foreground/45">
        <span>{job.gamesFetched} scanned</span>
        <span>{job.gamesNew} new</span>
        <span>{job.gamesSkipped} cached</span>
        {job.gamesUpdated > 0 && <span>{job.gamesUpdated} updated</span>}
        {job.archivesTotal > 0 && (
          <span>
            archive {job.archivesDone}/{job.archivesTotal}
          </span>
        )}
      </div>
    </div>
  );
}
