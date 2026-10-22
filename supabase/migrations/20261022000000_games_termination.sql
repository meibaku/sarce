-- How a game ended ("dratius won on time"), read from the PGN's Termination header. A generated column, so it is
-- filled for existing games and stays in sync; the You screen counts wins and losses on time without loading PGNs.
alter table public.games
  add column if not exists termination text
  generated always as (substring(pgn from 'Termination "([^"]+)"')) stored;
