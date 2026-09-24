# Better Budget

A budgeting app that plans as well as it records: it projects your cash day by day,
works out when each goal is actually met, and tells you what to move on which payday.

Three builds, all the same engine:

| file | storage | who it suits |
|---|---|---|
| `index.html` | Supabase, with accounts | you and anyone you share the URL with |
| `standalone.html` | the browser it runs in | one person, one device, no setup |
| *(your own copy)* | — | kept out of this repo by `.gitignore` |

## What it does

- **Envelope budget** — Budgeted / Actual / Remaining, with optional month-end rollover
- **Daily cash-flow simulator** in integer cents: real compounding, clamped due dates,
  mortgage escrow split, credit-card float that honours the grace period
- **Recurrence engine** across 13 frequencies. Month-end clamps and then *returns* to the
  anchor day, weekends shift to the nearer weekday, US federal holidays are observed —
  46 assertions run visibly in the page on the Schedule tab
- **Solver** that deploys spare cash on real paydays. Dated goals reserve capacity
  earliest-deadline-first; whatever is left cascades by priority and then by interest
  rate; projected cash never falls below your floor, which itself rises and falls as
  sinking funds fill and empty
- **Leftover sweep** — surplus beyond the funded goals compounds in an account you
  nominate rather than idling as cash
- **Import** of OFX/QFX and CSV, deduped on the bank's own transaction id, with rows
  matched to the planned bills they pay so nothing is projected twice

No build step, no framework, no dependencies. Each file is self-contained.

## Setting up accounts

See [SETUP.md](SETUP.md). Roughly: create a Supabase project, run `schema.sql`, paste
two public keys into `index.html`, publish. Budgets are separated by row-level security
in Postgres, not by anything the page does.

## Your data

Never in this repository. `standalone.html` keeps everything in the browser; the
Supabase build keeps it in your own account. **Data → Download backup** and
**Data → Restore** move it between devices.
