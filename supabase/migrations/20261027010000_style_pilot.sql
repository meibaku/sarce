-- Invite-only adult style pilot: admission, consent, feedback and exit evidence.

create table public.pilot_invitations (
  id uuid primary key default gen_random_uuid(),
  token_hash text not null unique check (length(token_hash) = 64),
  expires_at timestamptz not null,
  created_by uuid not null references auth.users (id),
  created_at timestamptz not null default now(),
  redeemed_by uuid references auth.users (id) on delete set null,
  redeemed_at timestamptz,
  check ((redeemed_by is null) = (redeemed_at is null))
);

alter table public.pilot_invitations enable row level security;
-- Invitations are intentionally service-role only; raw tokens are never stored.

create table public.pilot_consents (
  user_id uuid primary key references public.profiles (id) on delete cascade,
  invitation_id uuid not null unique references public.pilot_invitations (id),
  protocol_version text not null,
  privacy_version text not null,
  adult_confirmed boolean not null check (adult_confirmed),
  consented_at timestamptz not null default now(),
  withdrawn_at timestamptz
);

alter table public.pilot_consents enable row level security;
create policy "Participants can view own pilot consent"
  on public.pilot_consents for select using (auth.uid() = user_id);

create table public.pilot_read_feedback (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  game_id uuid not null references public.games (id) on delete cascade,
  resonance text not null check (resonance in ('yes', 'partly', 'no')),
  comment text check (comment is null or char_length(comment) <= 500),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, game_id)
);

alter table public.pilot_read_feedback enable row level security;
create policy "Participants can view own pilot feedback"
  on public.pilot_read_feedback for select using (auth.uid() = user_id);
create policy "Participants can add own pilot feedback"
  on public.pilot_read_feedback for insert with check (
    auth.uid() = user_id and exists (
      select 1 from public.games g where g.id = game_id and g.user_id = auth.uid()
    )
  );
create policy "Participants can update own pilot feedback"
  on public.pilot_read_feedback for update using (auth.uid() = user_id);

create table public.pilot_exit_surveys (
  user_id uuid primary key references public.profiles (id) on delete cascade,
  continue_using text not null check (continue_using in ('yes', 'maybe', 'no')),
  most_valuable text not null check (char_length(most_valuable) between 1 and 120),
  least_trusted text not null check (char_length(least_trusted) between 1 and 120),
  willingness_to_pay text not null check (willingness_to_pay in ('yes', 'maybe', 'no')),
  submitted_at timestamptz not null default now()
);

alter table public.pilot_exit_surveys enable row level security;
create policy "Participants can view own pilot exit survey"
  on public.pilot_exit_surveys for select using (auth.uid() = user_id);
create policy "Participants can add own pilot exit survey"
  on public.pilot_exit_surveys for insert with check (auth.uid() = user_id);
create policy "Participants can update own pilot exit survey"
  on public.pilot_exit_surveys for update using (auth.uid() = user_id);
