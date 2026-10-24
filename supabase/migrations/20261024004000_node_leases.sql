-- Paired Sarce Nodes (ADR 0010): which game each node is searching. A lease with no heartbeat for a few minutes
-- (a power cut, a closed laptop) returns its game to the pool; the server's own analysis skips live leases.
-- Written only by the node gateway with the service role, so no client policies.
create table if not exists public.node_leases (
  game_id uuid primary key references public.games (id) on delete cascade,
  node text not null check (char_length(node) <= 80),
  leased_at timestamptz not null default now(),
  heartbeat_at timestamptz not null default now(),
  done_at timestamptz,
  positions integer not null default 0
);

create index if not exists node_leases_live_idx on public.node_leases (done_at, heartbeat_at);

alter table public.node_leases enable row level security;

grant select, insert, update, delete on public.node_leases to service_role;
