-- Shared links (CHAOS_PLAN M8 sharing): a read-only page for one game summary or one sacrifice.
-- `snapshot` is captured when the link is made, so later notes or re-analysis never leak through it, and it
-- names no third party (the opponent is "an opponent"). Anyone with the token can read it through the
-- API; only the owner can list or revoke. Revoked links stop answering at once.
create table if not exists public.shared_links (
  id uuid primary key default gen_random_uuid(),
  token text not null unique,
  user_id uuid not null references public.profiles (id) on delete cascade,
  kind text not null check (kind in ('summary', 'sacrifice')),
  game_id uuid references public.games (id) on delete cascade,
  ply integer,
  snapshot jsonb not null,
  created_at timestamptz not null default now(),
  revoked_at timestamptz
);

create index if not exists shared_links_user_idx on public.shared_links (user_id, created_at desc);

alter table public.shared_links enable row level security;

create policy "Users can view own shared links"
  on public.shared_links for select using (user_id = auth.uid());

create policy "Users can create shared links"
  on public.shared_links for insert with check (user_id = auth.uid());

create policy "Users can revoke own shared links"
  on public.shared_links for update using (user_id = auth.uid());

create policy "Users can delete own shared links"
  on public.shared_links for delete using (user_id = auth.uid());

grant select, insert, update, delete on public.shared_links to service_role;
