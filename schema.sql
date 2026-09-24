-- Better Budget — Supabase schema
-- Run this once in the Supabase SQL editor (Dashboard → SQL Editor → New query).

-- One row per document, exactly mirroring the app's storage model:
--   core/settings, core/accounts, core/categories, core/recurrences, core/goals,
--   txns/YYYY-MM, budget/YYYY-MM
create table if not exists public.documents (
  user_id    uuid        not null references auth.users(id) on delete cascade,
  path       text        not null,
  data       jsonb       not null,
  updated_at timestamptz not null default now(),
  primary key (user_id, path)
);

-- Row Level Security is what keeps budgets apart. Without it every signed-in user
-- could read every other user's rows, because the anon key is public by design.
alter table public.documents enable row level security;

drop policy if exists "read own documents"   on public.documents;
drop policy if exists "insert own documents" on public.documents;
drop policy if exists "update own documents" on public.documents;
drop policy if exists "delete own documents" on public.documents;

create policy "read own documents" on public.documents
  for select using (auth.uid() = user_id);

create policy "insert own documents" on public.documents
  for insert with check (auth.uid() = user_id);

create policy "update own documents" on public.documents
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "delete own documents" on public.documents
  for delete using (auth.uid() = user_id);

-- Keep updated_at honest.
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

drop trigger if exists documents_touch on public.documents;
create trigger documents_touch before update on public.documents
  for each row execute function public.touch_updated_at();

-- Find a user's documents quickly.
create index if not exists documents_user_idx on public.documents (user_id);

-- Sanity check: this must return zero rows for a signed-out session.
-- select count(*) from public.documents;
