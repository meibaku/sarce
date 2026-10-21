-- Secondary move-analysis metadata for style review.

alter table public.game_moves
  add column if not exists san text,
  add column if not exists phase text check (phase in ('opening', 'middlegame', 'endgame')),
  add column if not exists signals jsonb not null default '[]'::jsonb,
  add column if not exists highlight text,
  add column if not exists best_uci text,
  add column if not exists best_san text,
  add column if not exists pv jsonb not null default '[]'::jsonb;
