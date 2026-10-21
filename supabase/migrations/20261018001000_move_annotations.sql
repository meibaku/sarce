-- v1.0 Review: the player's intent note on a moment ("I meant this"), written before the engine's
-- view is shown (docs/DESIGN.md). One note per move; editing replaces it.
create table if not exists public.move_annotations (
  id uuid primary key default gen_random_uuid(),
  game_id uuid not null references public.games (id) on delete cascade,
  ply integer not null,
  user_id uuid references auth.users (id) on delete cascade,
  intent_type text check (intent_type in ('calculated', 'intuitive', 'bluff')),
  note text not null default '' check (char_length(note) <= 2000),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (game_id, ply)
);

create index if not exists move_annotations_game_id_idx on public.move_annotations (game_id);

alter table public.move_annotations enable row level security;

create policy "Users can view notes for own games"
  on public.move_annotations for select
  using (exists (select 1 from public.games g where g.id = move_annotations.game_id and g.user_id = auth.uid()));

create policy "Users can write notes for own games"
  on public.move_annotations for insert
  with check (exists (select 1 from public.games g where g.id = move_annotations.game_id and g.user_id = auth.uid()));

create policy "Users can edit notes for own games"
  on public.move_annotations for update
  using (exists (select 1 from public.games g where g.id = move_annotations.game_id and g.user_id = auth.uid()))
  with check (exists (select 1 from public.games g where g.id = move_annotations.game_id and g.user_id = auth.uid()));

-- The API writes with the service role, as for the other Chaos Lens tables.
grant select, insert, update, delete on public.move_annotations to service_role;
