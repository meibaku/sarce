-- Answers to the after-game questions beyond "felt like you" (docs/DESIGN.md): the random check-in
-- ("Was something going on here?") and how today's intention went. `flagged` records whether the
-- distraction detector had flagged the move, so its precision and recall can be measured against
-- unflagged control moments.
create table if not exists public.game_answers (
  id uuid primary key default gen_random_uuid(),
  game_id uuid not null references public.games (id) on delete cascade,
  kind text not null check (kind in ('checkin')),
  ply integer,
  answer text not null check (answer in ('distracted', 'time_pressure', 'on_purpose', 'nothing')),
  flagged boolean,
  created_at timestamptz not null default now(),
  unique (game_id, kind, ply)
);

create index if not exists game_answers_game_id_idx on public.game_answers (game_id);

alter table public.game_answers enable row level security;

create policy "Users can view answers for own games"
  on public.game_answers for select
  using (exists (select 1 from public.games g where g.id = game_answers.game_id and g.user_id = auth.uid()));

create policy "Users can answer for own games"
  on public.game_answers for insert
  with check (exists (select 1 from public.games g where g.id = game_answers.game_id and g.user_id = auth.uid()));

grant select, insert, update, delete on public.game_answers to service_role;
