-- Chaos Lens M6 — rating-band trap atlas (docs/CHAOS_PLAN.md).
-- Positions where the reply most often played at a rating band loses a lot of expected points.
-- Aggregated from finished public games; contains no player identities.

create table public.trap_atlas (
  -- FEN without the fullmove number (same key as position_evals).
  fen_key text not null,
  -- Full FEN, for rendering the position.
  fen text not null,
  -- Lower edge of a 200-point rating band.
  band int not null check (band between 0 and 4000),
  speed text not null,
  frequency int not null check (frequency > 0),
  common_reply_uci text not null,
  common_reply_share numeric not null check (common_reply_share between 0 and 1),
  -- Mean expected points lost by the common reply.
  ep_loss numeric not null,
  best_reply_uci text,
  p_fail numeric,
  stake numeric,
  eco text,
  created_at timestamptz not null default now(),
  primary key (fen_key, band, speed)
);

create index trap_atlas_band_idx on public.trap_atlas (band, ep_loss desc);

alter table public.trap_atlas enable row level security;

create policy "Trap atlas is readable by authenticated users"
  on public.trap_atlas for select
  to authenticated
  using (true);

grant select, insert, update, delete on public.trap_atlas to service_role;
