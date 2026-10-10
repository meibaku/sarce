-- Chaos Lens M1 — raw engine data (docs/CHAOS_PLAN.md).
-- position_evals: node-limited MultiPV evaluations cached by position, written by the API.
-- games.clocks_ms: remaining clock per ply for both players, parsed from PGN %clk comments.

create table public.position_evals (
  -- FEN without the fullmove number; the halfmove clock is kept (fifty-move rule).
  fen_key text not null,
  nodes int not null check (nodes > 0),
  multipv int not null check (multipv > 0),
  -- Best first, side to move's perspective: [{move_uci, cp, mate, wdl, ep}]
  lines jsonb not null default '[]'::jsonb,
  -- False when the MultiPV cap stopped widening before a line fell outside the safe tolerance.
  safe_set_complete boolean not null default false,
  engine_version text not null,
  created_at timestamptz not null default now(),
  primary key (fen_key, nodes)
);

alter table public.position_evals enable row level security;

-- Positions are not user data: any signed-in user may read; only the API (service role) writes.
create policy "Position evals are readable by authenticated users"
  on public.position_evals for select
  to authenticated
  using (true);

grant select, insert, update, delete on public.position_evals to service_role;

-- Index = ply; each value is the mover's remaining milliseconds after that move, or null.
alter table public.games
  add column if not exists clocks_ms jsonb;
