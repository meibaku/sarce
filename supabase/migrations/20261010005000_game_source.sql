-- Chaos Lens M8 — Lichess import (docs/CHAOS_PLAN.md).
-- Which site a game came from. Existing rows are Chess.com games.
-- `chess_com_username` keeps its name for compatibility; for Lichess games it holds the Lichess handle.

alter table public.games
  add column if not exists source text not null default 'chess_com'
    check (source in ('chess_com', 'lichess'));
