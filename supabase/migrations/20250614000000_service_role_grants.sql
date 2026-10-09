grant usage on schema public to service_role;

grant select, insert, update, delete on table public.profiles to service_role;
grant select, insert, update, delete on table public.games to service_role;
grant select, insert, update, delete on table public.game_moves to service_role;
grant select, insert, update, delete on table public.game_analyses to service_role;
grant select, insert, update, delete on table public.user_baselines to service_role;
grant select, insert, update, delete on table public.reference_players to service_role;
grant select, insert, update, delete on table public.reference_benchmarks to service_role;
grant select, insert, update, delete on table public.style_vectors to service_role;
