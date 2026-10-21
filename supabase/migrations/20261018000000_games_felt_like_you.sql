-- v1.0 Summary: the player's answer to "Did this game feel like you?" (docs/DESIGN.md).
-- Kept next to the game; the timeline shows both the style read and the answer when they differ.
alter table public.games
  add column if not exists felt_like_you text
    check (felt_like_you in ('yes', 'partly', 'no')),
  add column if not exists felt_at timestamptz;

-- Players may record their own answer (the API writes with the service role in local-first mode).
create policy "Users can update own game answers"
  on public.games for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
