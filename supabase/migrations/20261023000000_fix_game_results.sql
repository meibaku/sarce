-- Repair games.result. The Chess.com import read White's own outcome code backwards ("resigned", "timeout" and
-- "abandoned" counted as White wins; every draw code as a White loss), inverting about a third of results. The
-- parser now uses the PGN's [Result] header (app/services/pgn_parser.py); this recomputes stored rows the same way.
-- Rows without a decisive or drawn header ("*" or missing) are left as they are.
update public.games g
set result = fixed.result
from (
  select id,
    case
      when r = '1/2-1/2' then 'draw'
      when (r = '1-0' and user_color = 'white') or (r = '0-1' and user_color = 'black') then 'win'
      else 'loss'
    end as result
  from (
    select id, user_color, substring(pgn from 'Result "([^"]+)"') as r
    from public.games
  ) parsed
  where r in ('1-0', '0-1', '1/2-1/2') and user_color in ('white', 'black')
) fixed
where g.id = fixed.id and g.result is distinct from fixed.result;
