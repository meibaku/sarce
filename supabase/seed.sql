-- Local development seed
-- Run via: supabase db reset (applies migrations + seed)

-- Fixed local user for API-only dev (no login required)
insert into auth.users (
  id,
  instance_id,
  aud,
  role,
  email,
  encrypted_password,
  email_confirmed_at,
  created_at,
  updated_at,
  confirmation_token,
  recovery_token,
  email_change_token_new,
  email_change
)
values (
  '00000000-0000-4000-8000-000000000001',
  '00000000-0000-0000-0000-000000000000',
  'authenticated',
  'authenticated',
  'local@sarce.dev',
  crypt('localdev', gen_salt('bf')),
  now(),
  now(),
  now(),
  '',
  '',
  '',
  ''
)
on conflict (id) do nothing;

-- Profile created by trigger; ensure chess.com username placeholder
update public.profiles
set chess_com_username = coalesce(chess_com_username, 'local-dev')
where id = '00000000-0000-4000-8000-000000000001';
