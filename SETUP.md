# Setting up Better Budget with accounts

Anyone who signs up gets their own budget. Nobody can see anyone else's.

## 1. Create the Supabase project

1. supabase.com → **New project** (free tier is plenty)
2. Pick a name and a strong database password — you won't need the password again
3. Wait a minute or two for it to provision

## 2. Create the table

Dashboard → **SQL Editor** → **New query** → paste the whole of `schema.sql` → **Run**.

That creates one table and turns on row-level security. The policies are what keep
budgets apart — they are enforced by Postgres, not by the web page, so nothing a
browser does can reach another person's rows.

## 3. Put your keys into the app

Dashboard → **Project Settings** → **API**. Copy:

- **Project URL** — looks like `https://abcdefgh.supabase.co`
- **anon public** key — a long string starting `eyJ...`

Open `index.html` and replace the two placeholders near the top of the script:

```js
const SUPABASE_URL      = "https://abcdefgh.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOi...";
```

**Both are meant to be public.** The anon key identifies the project, not a person —
it can only ever act as whoever is signed in, and row-level security does the rest.
It is safe in a public repository. Your database password and the `service_role` key
are the secrets; never put either in this file.

## 4. Decide about email confirmation

Dashboard → **Authentication** → **Providers** → **Email**.

- **Confirm email ON** (default) — people must click a link before signing in. Safer,
  but the free tier sends a limited number of emails per hour.
- **Confirm email OFF** — sign-up works immediately. Fine for you and a few friends.

## 5. Publish

Commit and push, then enable GitHub Pages on the repo. Share the URL with your friends;
each of them presses **Create an account** once.

## Moving your existing budget in

Sign in, go to **Data → Restore**, and load your `better-budget-backup.json`. It lands
in your account and follows you to any device you sign in on.

## What each person gets

Their own accounts, categories, recurring rows, goals, transactions and budgets — the
whole app, on any device, synced. No manual backup shuffling.

## If something goes wrong

- **"Invalid login credentials"** — wrong password, or the account was never confirmed.
- **Signed in but no data, and saving fails** — `schema.sql` did not run, or ran against
  a different project than the keys point at.
- **Nothing loads at all** — check the browser console; usually the URL or key is wrong.
- **Forgotten password** — Dashboard → Authentication → Users → send a reset link.
