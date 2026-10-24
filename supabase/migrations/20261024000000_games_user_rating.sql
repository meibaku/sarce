-- Your own rating in each game, read from the PGN's WhiteElo/BlackElo header for your colour (review F11a: the
-- Brilliant find-rate clause is judged at the mover's rating, converted to the human model's scale in
-- app/services/rating_map.py). A generated column, so existing games are filled and it stays in sync.
alter table public.games
  add column if not exists user_rating integer
  generated always as (
    nullif(substring(pgn from case when user_color = 'black' then 'BlackElo "([0-9]+)"' else 'WhiteElo "([0-9]+)"' end), '')::integer
  ) stored;
