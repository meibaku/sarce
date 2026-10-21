-- ECO extraction (PHASES 1.8, design handoff "before shipping" 2): the opening of every game, for
-- "Tal in your openings" in Train, traps in your openings and the library's opening filter.
-- Backfilled from the PGN headers already stored: [ECO], and the name from Lichess's [Opening] or the
-- last part of Chess.com's [ECOUrl] (moves after the name, like "-3.Nf3", are dropped).

alter table public.games add column if not exists eco text;
alter table public.games add column if not exists opening text;

update public.games
set
  eco = substring(pgn from '\[ECO "([A-E][0-9]{2})"\]'),
  opening = coalesce(
    substring(pgn from '\[Opening "([^"]+)"\]'),
    nullif(replace(regexp_replace(substring(pgn from '\[ECOUrl "[^"]*/openings/([^"]+)"\]'), '-[0-9].*$', ''), '-', ' '), '')
  )
where eco is null and pgn is not null;

create index if not exists games_user_eco_idx on public.games (user_id, eco);
