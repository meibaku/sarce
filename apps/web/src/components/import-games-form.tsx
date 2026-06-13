"use client";

interface ImportGamesFormProps {
  onImport: (username: string) => void;
  loading: boolean;
}

export function ImportGamesForm({ onImport, loading }: ImportGamesFormProps) {
  return (
    <form
      className="rounded-xl border border-white/10 bg-surface p-6"
      onSubmit={(e) => {
        e.preventDefault();
        const form = e.currentTarget;
        const username = new FormData(form).get("username") as string;
        if (username.trim()) onImport(username.trim());
      }}
    >
      <h2 className="text-lg font-medium">Import from Chess.com</h2>
      <p className="mt-1 text-sm text-foreground/60">
        Fetch your recent public games and run style analysis.
      </p>
      <div className="mt-4 flex gap-3">
        <input
          name="username"
          type="text"
          placeholder="Chess.com username"
          className="flex-1 rounded-lg border border-white/10 bg-background px-4 py-2 text-sm outline-none focus:border-accent/50"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-background transition hover:bg-accent/90 disabled:opacity-50"
        >
          {loading ? "Importing…" : "Import games"}
        </button>
      </div>
    </form>
  );
}
