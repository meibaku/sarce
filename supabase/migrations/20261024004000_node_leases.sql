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

-- Claim a game for one node worker, atomically: its own unfinished game if it still has one (after a power cut),
-- else the newest pending game with no live or finished lease. `for update skip locked` and the conditional
-- upsert mean two workers asking at once never get the same game. Returns null when there is nothing to do.
create or replace function public.claim_node_game(p_node text, p_lease_s integer)
returns uuid
language plpgsql
security invoker
set search_path = public
as $$
declare
  g uuid;
begin
  -- Leases this node holds on games that no longer need searching are closed.
  update node_leases l set done_at = now()
   where l.node = p_node and l.done_at is null
     and exists (select 1 from games ga where ga.id = l.game_id and ga.analysis_status <> 'pending');

  select l.game_id into g
    from node_leases l join games ga on ga.id = l.game_id
   where l.node = p_node and l.done_at is null and ga.analysis_status = 'pending'
   limit 1;

  if g is null then
    select ga.id into g
      from games ga
     where ga.analysis_status = 'pending' and ga.pgn is not null
       and not exists (
         select 1 from node_leases l
          where l.game_id = ga.id
            and (l.done_at is not null or l.heartbeat_at > now() - make_interval(secs => p_lease_s))
       )
     order by ga.played_at desc nulls last
     limit 1
     for update of ga skip locked;
    if g is null then
      return null;
    end if;
  end if;

  insert into node_leases (game_id, node, leased_at, heartbeat_at, done_at, positions)
  values (g, p_node, now(), now(), null, 0)
  on conflict (game_id) do update
     set node = excluded.node, leased_at = now(), heartbeat_at = now(), done_at = null
   where node_leases.node = excluded.node
      or node_leases.heartbeat_at <= now() - make_interval(secs => p_lease_s);

  if not exists (select 1 from node_leases where game_id = g and node = p_node and done_at is null) then
    return null;  -- another worker won it in the meantime; the caller asks again
  end if;
  return g;
end;
$$;

revoke all on function public.claim_node_game(text, integer) from public, anon, authenticated;
grant execute on function public.claim_node_game(text, integer) to service_role;
