import { Dashboard } from "@/components/dashboard";

export default function Home() {
  return (
    <main className="min-h-screen">
      <header className="border-b border-white/10 bg-surface/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-accent-muted">
              Chess style analysis
            </p>
            <h1 className="text-2xl font-semibold tracking-tight">Sarce</h1>
          </div>
          <p className="text-sm text-foreground/60">Tal-style target: 6–10% Brilliant</p>
        </div>
      </header>
      <Dashboard />
    </main>
  );
}
