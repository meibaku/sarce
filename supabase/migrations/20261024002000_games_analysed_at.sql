-- When a game's analysis completed (plan 3.4a): Home's "since your last visit" line counts games by when they were
-- analysed, not when they were played, so a game imported late or analysed after a visit is still counted once.
alter table public.games add column if not exists analysed_at timestamptz;
create index if not exists games_user_analysed_at_idx on public.games (user_id, analysed_at);
