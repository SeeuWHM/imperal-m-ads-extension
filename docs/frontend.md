# Microsoft Ads — Frontend Status

> This file is maintained by the designer and their Claude.
> Update it as you work: what's done, decisions made, open questions.

---

## Current State (as of 2026-04-23)

The backend is **100% complete** — 30 functions, all tested and working.

The panels exist but were written by a developer, not a designer.
They are **functional** (all states wired, data connected) but need proper design.

### Files to redesign

| File | What it contains | Status |
|------|-----------------|--------|
| `panels.py` | Left panel: account dashboard | Functional draft — needs design |
| `panels_campaign.py` | Right panel: campaign detail | Functional draft — needs design |
| `panels_ui.py` | Shared helpers: formatters, badges, OAuth view | Reusable, extend as needed |

---

## What exists in the panels (read before changing)

### Left panel (`panels.py`) — 7 states

1. **not_connected** — Connect button with OAuth URL (`ui.Open`)
2. **needs_setup / no_customers** — Warning, "try different account" button
3. **needs_setup / 1 customer** — Auto-activates, shows success + refresh
4. **needs_setup / multiple customers** — Account picker list (`ui.List` + `ui.ListItem`)
5. **loading_error** — Skeleton missing after setup, shows warning + retry
6. **dashboard** — Full view: Header, budget progress bar, KPI stats (2 columns),
   campaign divider, campaigns list with pause/resume actions, footer with "+ Campaign"

### Right panel (`panels_campaign.py`) — 3 states

1. **empty** — "Select a campaign from the left panel"
2. **error** — API failure with retry button
3. **loaded** — Header (name + badge) + Settings stats (3 columns: budget/bidding/status)
   + Tabs: "Today" (spend chart + KPI stats) · "Ad Groups (N)" (list with Keywords/Ads actions)
   + Footer: Pause/Resume · 7-day report · AI Analyse

---

## Design TODO

> Fill this in as you plan and execute the redesign.

- [ ] Left panel: account dashboard
- [ ] Left panel: not_connected view
- [ ] Left panel: account picker (multi-account)
- [ ] Right panel: campaign detail header
- [ ] Right panel: Today tab (chart + KPIs)
- [ ] Right panel: Ad Groups tab
- [ ] Shared: badge styles (Active/Paused/Deleted)
- [ ] Shared: formatters review (currency, percentage, number)

---

## Design Decisions

> Document design choices here as you make them.

---

## Open Questions

> Questions for SeeU — he'll answer in the PR or here.

---

## Notes

> Anything else worth remembering.
