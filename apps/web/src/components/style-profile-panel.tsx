import type { StyleProfile } from "@/types/chess";

interface StyleProfilePanelProps {
  profile: StyleProfile | null;
}

const SIGNAL_NAMES: Record<string, string> = {
  brilliant_sacrifice: "Sound sacrifices",
  sacrifice: "Sacrifices",
  exchange_sacrifice: "Exchange sacs",
  breakthrough_sacrifice: "Breakthroughs",
  tactical_resource: "Tactics",
  momentum_shift: "Momentum shifts",
  evaluation_swing: "Eval swings",
  missed_tactic: "Missed tactics",
  critical_error: "Critical errors",
  clearly_best: "Clearly best",
};

function topEntries(values: Record<string, number>, limit = 5) {
  return Object.entries(values)
    .filter(([, value]) => value > 0)
    .sort(([, a], [, b]) => b - a)
    .slice(0, limit);
}

export function StyleProfilePanel({ profile }: StyleProfilePanelProps) {
  const phaseEntries = topEntries(profile?.phaseDistribution ?? {}, 3);
  const signalEntries = topEntries(profile?.signalDistribution ?? {}, 6);
  const resultEntries = topEntries(profile?.resultDistribution ?? {}, 3);
  const maxSignal = Math.max(...signalEntries.map(([, value]) => value), 1);
  const maxPhase = Math.max(...phaseEntries.map(([, value]) => value), 1);

  return (
    <section className="rounded-xl border border-white/10 bg-surface p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-foreground/45">
            Player profile
          </p>
          <h2 className="mt-1 text-xl font-semibold">
            {profile?.styleLabel ?? "No analyzed style yet"}
          </h2>
          <p className="mt-2 text-sm text-foreground/55">
            {profile?.favoriteOpening
              ? `${profile.favoriteOpening.eco ? `${profile.favoriteOpening.eco} ` : ""}${profile.favoriteOpening.name}`
              : "Favorite opening will appear after analysis."}
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center">
          <MiniStat label="Games" value={`${profile?.gamesAnalyzed ?? 0}`} />
          <MiniStat
            label="Openings"
            value={`${profile?.openings.length ?? 0}`}
          />
          <MiniStat
            label="Signals"
            value={`${Object.values(profile?.signalDistribution ?? {}).reduce((a, b) => a + b, 0)}`}
          />
        </div>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[1fr_1fr_1fr]">
        <div>
          <h3 className="mb-3 text-sm font-medium text-foreground/75">
            Type of Play
          </h3>
          <div className="space-y-2">
            {signalEntries.map(([signal, count]) => (
              <Bar
                key={signal}
                label={SIGNAL_NAMES[signal] ?? signal.replaceAll("_", " ")}
                value={count}
                max={maxSignal}
              />
            ))}
            {signalEntries.length === 0 && <EmptyLine />}
          </div>
        </div>

        <div>
          <h3 className="mb-3 text-sm font-medium text-foreground/75">
            Game Phase
          </h3>
          <div className="space-y-2">
            {phaseEntries.map(([phase, count]) => (
              <Bar key={phase} label={phase} value={count} max={maxPhase} />
            ))}
            {phaseEntries.length === 0 && <EmptyLine />}
          </div>
        </div>

        <div>
          <h3 className="mb-3 text-sm font-medium text-foreground/75">
            Favorite Openings
          </h3>
          <div className="space-y-2">
            {(profile?.openings ?? []).slice(0, 4).map((opening) => (
              <div
                key={`${opening.eco}-${opening.name}`}
                className="rounded-md border border-white/10 bg-background/35 px-3 py-2"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="truncate text-sm">{opening.name}</span>
                  <span className="text-xs text-foreground/45">
                    {opening.games}
                  </span>
                </div>
                {opening.eco && (
                  <div className="mt-1 text-xs text-foreground/40">
                    {opening.eco}
                  </div>
                )}
              </div>
            ))}
            {(!profile || profile.openings.length === 0) && <EmptyLine />}
          </div>
        </div>
      </div>

      {resultEntries.length > 0 && (
        <div className="mt-5 flex flex-wrap gap-2">
          {resultEntries.map(([result, count]) => (
            <span
              key={result}
              className="rounded border border-white/10 bg-background/35 px-2 py-1 text-xs capitalize text-foreground/55"
            >
              {result}: {count}
            </span>
          ))}
        </div>
      )}
    </section>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-white/10 bg-background/35 px-3 py-2">
      <div className="text-xs uppercase tracking-[0.12em] text-foreground/40">
        {label}
      </div>
      <div className="mt-1 text-lg font-semibold">{value}</div>
    </div>
  );
}

function Bar({
  label,
  value,
  max,
}: {
  label: string;
  value: number;
  max: number;
}) {
  return (
    <div className="rounded-md border border-white/10 bg-background/35 px-3 py-2">
      <div className="mb-2 flex items-center justify-between gap-3 text-sm">
        <span className="truncate capitalize">{label}</span>
        <span className="text-xs text-foreground/45">{value}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-accent"
          style={{ width: `${Math.max(6, (value / max) * 100)}%` }}
        />
      </div>
    </div>
  );
}

function EmptyLine() {
  return (
    <div className="rounded-md border border-white/10 bg-background/35 px-3 py-6 text-sm text-foreground/45">
      Waiting for analyzed games
    </div>
  );
}
