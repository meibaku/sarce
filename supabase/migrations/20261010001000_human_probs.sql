-- Chaos Lens M2 — human move probabilities (docs/CHAOS_PLAN.md).
-- human_probs: P(move | position, Elo) from the configured human model, cached per position.

create table public.human_probs (
  -- Same key as position_evals: FEN without the fullmove number.
  fen_key text not null,
  elo int not null check (elo between 0 and 4000),
  -- "<model name>-<version>"; a new model or version never overwrites older rows.
  model_version text not null,
  -- {uci: probability} covering every legal move, summing to 1.
  probs jsonb not null,
  created_at timestamptz not null default now(),
  primary key (fen_key, elo, model_version)
);

alter table public.human_probs enable row level security;

-- Not user data: any signed-in user may read; only the API (service role) writes.
create policy "Human probs are readable by authenticated users"
  on public.human_probs for select
  to authenticated
  using (true);

grant select, insert, update, delete on public.human_probs to service_role;
