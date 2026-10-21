-- Chaos Lens M3 — lens results per user move (docs/CHAOS_PLAN.md).
-- Derived data: recomputed from position_evals + human_probs without any engine run.

create table public.move_lens_scores (
  game_move_id uuid not null references public.game_moves (id) on delete cascade,
  -- Denormalized so per-user summaries need a single join.
  game_id uuid not null references public.games (id) on delete cascade,
  ply int not null,
  lens text not null,
  lens_version text not null,
  score numeric,
  verdict text,
  -- Lens-specific: P_fail per Elo, stake, safe set, objective cost, ...
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  primary key (game_move_id, lens)
);

create index move_lens_scores_game_id_idx on public.move_lens_scores (game_id);

alter table public.move_lens_scores enable row level security;

create policy "Users can view lens scores for own games"
  on public.move_lens_scores for select
  using (
    exists (
      select 1 from public.games g
      where g.id = move_lens_scores.game_id and g.user_id = auth.uid()
    )
  );

grant select, insert, update, delete on public.move_lens_scores to service_role;
