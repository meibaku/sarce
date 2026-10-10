"use client";

export type GameSource = "chess_com" | "lichess";

interface ImportGamesFormProps {
  onImport: (username: string, source: GameSource) => void;
  loading: boolean;
}

export function ImportGamesForm({ onImport, loading }: ImportGamesFormProps) {
  return (
    <form
      className="rounded-xl border border-white/10 bg-surface p-6"
      onSubmit={(e) => {
        e.preventDefault();
        const form = e.currentTarget;
        const data = new FormData(form);
        const username = data.get("username") as string;
        if (username.trim()) onImport(username.trim(), data.get("source") as GameSource);
      }}
    >
      <h2 className="text-lg font-medium">Import your games</h2>
      <p className="mt-1 text-sm text-foreground/60">
        Fetch public finished games for the username from Chess.com or Lichess.
      </p>
      <div className="mt-4 flex gap-3">
        <select
          name="source"
          aria-label="Site"
          defaultValue="chess_com"
          className="rounded-lg border border-white/10 bg-background px-3 py-2 text-sm outline-none focus:border-accent/50"
          disabled={loading}
        >
          <option value="chess_com">Chess.com</option>
          <option value="lichess">Lichess</option>
        </select>
        <input
          name="username"
          type="text"
          placeholder="Username"
          className="flex-1 rounded-lg border border-white/10 bg-background px-4 py-2 text-sm outline-none focus:border-accent/50"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-background transition hover:bg-accent/90 disabled:opacity-50"
        >
          {loading ? "Importing..." : "Import games"}
        </button>
      </div>
    </form>
  );
}
