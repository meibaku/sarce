-- Your traps (app/services/traps_set.py): opening positions you steer into where opponents most often go wrong on
-- the next move, from your own finished games and stored evaluations. Rebuilt on request: the API replaces a
-- player's rows as a set.
create table if not exists public.traps_set (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  fen text not null,
  fen_key text not null,
  line text not null,
  user_move text not null,
  seen integer not null,
  caught integer not null,
  rate real not null,
  gain_cp integer not null,
  slip text not null,
  defence text not null,
  computed_at timestamptz not null default now(),
  unique (user_id, fen_key)
);

alter table public.traps_set enable row level security;

create policy "Users can view own traps"
  on public.traps_set for select using (user_id = auth.uid());

grant select, insert, update, delete on public.traps_set to service_role;
