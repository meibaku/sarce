import type { ChaosSummary } from "@/types/chess";

interface ChaosSummaryPanelProps {
  summary: ChaosSummary | null;
}

export function ChaosSummaryPanel({ summary }: ChaosSummaryPanelProps) {
  const flagged = summary
    ? summary.realChaos + summary.calculatedRisk + summary.cheapChaos
    : 0;

  if (!summary || (flagged === 0 && summary.problemsFaced === 0)) {
    return (
      <section className="rounded-xl border border-white/10 bg-surface p-6">
        <h2 className="text-lg font-medium">Chaos control</h2>
        <p className="mt-2 text-sm text-foreground/60">
          No chaos data yet. Once position evaluations are enabled, this shows how
          often your moves set real problems and how often you solve the ones set
          for you.
        </p>
      </section>
    );
  }

  const share = (count: number) => (flagged ? (count / flagged) * 100 : 0);
  const recent = summary.perGame.slice(-20);
  const peak = Math.max(1, ...recent.map((g) => g.realChaos + g.cheapChaos));

  return (
    <section className="rounded-xl border border-white/10 bg-surface p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-medium">Chaos control</h2>
        <p className="text-xs text-foreground/40">
          Interim human model — estimates are not yet calibrated
        </p>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-4">
        <Tile label="Real chaos" value={`${summary.realChaos}`} tone="text-brilliant" />
        <Tile label="Calculated risk" value={`${summary.calculatedRisk}`} tone="text-amber-100" />
        <Tile label="Cheap chaos" value={`${summary.cheapChaos}`} tone="text-orange-100" />
        <Tile
          label="Survival rate"
          value={
            summary.survivalRate == null
              ? "-"
              : `${Math.round(summary.survivalRate * 100)}%`
          }
          hint={`${summary.survived} of ${summary.problemsFaced} problems solved`}
          tone="text-emerald-200"
        />
      </div>

      {flagged > 0 && (
        <div className="mt-4">
          <p className="mb-1 text-xs text-foreground/45">
            Mix of the {flagged} moves that created real trouble
          </p>
          <div className="flex h-2 overflow-hidden rounded bg-surface-elevated">
            <div className="bg-brilliant" style={{ width: `${share(summary.realChaos)}%` }} />
            <div className="bg-amber-400/70" style={{ width: `${share(summary.calculatedRisk)}%` }} />
            <div className="bg-orange-400/70" style={{ width: `${share(summary.cheapChaos)}%` }} />
          </div>
        </div>
      )}

      {recent.length > 1 && (
        <div className="mt-5">
          <p className="mb-1 text-xs text-foreground/45">
            Real vs cheap chaos over your last {recent.length} games
          </p>
          <div className="flex h-16 items-end gap-1">
            {recent.map((game) => (
              <div
                key={game.gameId}
                className="flex flex-1 flex-col justify-end"
                title={`${game.playedAt?.slice(0, 10) ?? "game"} — real ${game.realChaos}, cheap ${game.cheapChaos}`}
                style={{ height: "100%" }}
              >
                <div
                  className="rounded-t bg-orange-400/70"
                  style={{ height: `${(game.cheapChaos / peak) * 100}%` }}
                />
                <div
                  className="bg-brilliant"
                  style={{ height: `${(game.realChaos / peak) * 100}%` }}
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function Tile({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint?: string;
  tone: string;
}) {
  return (
    <div className="rounded-md border border-white/10 bg-background/40 px-4 py-3">
      <p className="text-xs text-foreground/45">{label}</p>
      <p className={`mt-1 font-mono text-2xl ${tone}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-foreground/45">{hint}</p>}
    </div>
  );
}
