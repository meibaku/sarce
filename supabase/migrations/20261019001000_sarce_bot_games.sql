-- Games against Sarce bots are saved for review (docs/DESIGN.md, screen 9).
-- They are practice: style metrics (Brilliant %, fingerprint, recap, library) leave them out.

alter table public.games drop constraint if exists games_source_check;
alter table public.games
  add constraint games_source_check check (source in ('chess_com', 'lichess', 'sarce_bot'));
