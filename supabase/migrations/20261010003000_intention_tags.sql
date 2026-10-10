-- Chaos Lens M7 — intention tagger (docs/CHAOS_PLAN.md).
-- move_tags: tactical motifs per ply, both players. game_ideas: the user's idea windows.
-- Derived data: recomputed from the PGN and stored Phase 1 evals, no engine run.

create table public.move_tags (
  game_id uuid not null references public.games (id) on delete cascade,
  ply int not null,
  by_user boolean not null,
  tag text not null check (tag in (
    'sacrifice', 'fork', 'pin', 'skewer', 'discovered_attack', 'hanging_piece'
  )),
  created_at timestamptz not null default now(),
  primary key (game_id, ply, tag)
);

alter table public.move_tags enable row level security;

create policy "Users can view tags for own games"
  on public.move_tags for select
  using (
    exists (
      select 1 from public.games g
      where g.id = move_tags.game_id and g.user_id = auth.uid()
    )
  );

grant select, insert, update, delete on public.move_tags to service_role;

create table public.game_ideas (
  id uuid primary key default gen_random_uuid(),
  game_id uuid not null references public.games (id) on delete cascade,
  family text not null check (family in ('gambit', 'king_attack', 'squeeze')),
  start_ply int not null,
  end_ply int not null check (end_ply >= start_ply),
  verdict text not null check (verdict in ('worked', 'refuted', 'fizzled')),
  -- A different idea family started soon after a refuted one.
  is_pivot boolean not null default false,
  created_at timestamptz not null default now()
);

create index game_ideas_game_id_idx on public.game_ideas (game_id);

alter table public.game_ideas enable row level security;

create policy "Users can view ideas for own games"
  on public.game_ideas for select
  using (
    exists (
      select 1 from public.games g
      where g.id = game_ideas.game_id and g.user_id = auth.uid()
    )
  );

grant select, insert, update, delete on public.game_ideas to service_role;
