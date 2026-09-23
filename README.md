# Better Budget

A single-file budgeting app. No build step, no dependencies, no account, no server.

## What it does

- **Envelope budget** — Budgeted / Actual / Remaining, with optional month-end rollover
- **Daily cash-flow simulator** in integer cents: real compounding, clamped due dates,
  mortgage escrow split, credit-card float with grace period
- **Recurrence engine** across 13 frequencies, with month-end clamping that returns to
  the anchor day, business-day shifting and US federal holidays — 46 assertions run
  visibly in the page on the Schedule tab
- **Solver** that deploys spare cash on real paydays, reserving capacity for dated goals
  earliest-deadline-first and never letting projected cash fall below your floor
- **Import** of OFX/QFX and CSV, deduped on the bank's own transaction id

## Your data

Stored in your browser, on your device. Nothing is transmitted — there is nowhere for it
to go. This repository contains the application only; it holds no financial data.

**Data → Download backup** saves a copy. **Data → Restore** loads one.

## Hosting

Settings → Pages → Deploy from branch → `main` / root.
