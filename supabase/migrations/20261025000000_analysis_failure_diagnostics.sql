-- Durable analysis retry budget and operator-only failure diagnostics.
alter table public.games
  add column if not exists analysis_attempts smallint not null default 0,
  add column if not exists analysis_error text,
  add column if not exists analysis_failed_at timestamptz;

alter table public.games
  add constraint games_analysis_attempts_nonnegative check (analysis_attempts >= 0) not valid;

comment on column public.games.analysis_error is
  'Bounded, sanitized operator diagnostic for the most recent analysis failure.';

-- RLS limits rows, not columns. Preserve client reads of game data while keeping failure diagnostics operator-only.
revoke select on public.games from anon, authenticated;
grant select (
  id, user_id, chess_com_username, external_id, pgn, played_at, opponent, opponent_rating,
  time_control, result, user_color, analysis_status, created_at, clocks_ms, chaos_data_status,
  source, felt_like_you, felt_at, eco, opening, termination, user_rating, analysed_at, analysis_attempts
) on public.games to anon, authenticated;
