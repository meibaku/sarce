-- Positions from videos (PHASES 2.2-2.4): where a saved position came from and what was said about it.
-- `source_url` / `source_time_s` point back to the video moment; `excerpt` is the transcript around it
-- (YouTube captions); `ai_summary` is the opt-in Claude summary of that excerpt.
alter table public.saved_positions add column if not exists source_url text;
alter table public.saved_positions add column if not exists source_time_s integer;
alter table public.saved_positions add column if not exists excerpt text not null default '';
alter table public.saved_positions add column if not exists ai_summary text not null default '';
