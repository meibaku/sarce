-- Threat raw data for the prophylaxis lens (app/services/threats.py): for a position the user faced, the opponent's
-- best move and score if the user passed (a null-move search). Engine output about positions, shared like
-- position_evals: no user data, so RLS is on with no policies and only the service role reads or writes it.
create table if not exists public.position_threats (
  fen_key text not null,
  nodes integer not null,
  threat_uci text not null,
  threat_cp real not null,
  created_at timestamptz not null default now(),
  primary key (fen_key, nodes)
);

alter table public.position_threats enable row level security;

grant select, insert, update, delete on public.position_threats to service_role;
