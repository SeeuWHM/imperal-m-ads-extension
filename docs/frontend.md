# Microsoft Ads — Frontend Status

> This file is maintained by the designer and their Claude.
> Update it as you work: what's done, decisions made, open questions.

---

## Current State (as of 2026-04-26)

The backend is **100% complete** — 30 functions, all tested and working.

The panels exist but were written by a developer, not a designer.
They are **functional** (all states wired, data connected) but need proper design.

### Current file structure (designer updated)

| File | What it contains | Status |
|------|-----------------|--------|
| `panels.py` | Left panel: account dashboard (all states) | Functional draft — needs design |
| `panels_campaign.py` | Right panel router (mode/campaign_id dispatch) | Refactored by designer |
| `panels_campaign_create.py` | Create campaign form (ui.Form) | ✅ Built by designer (PR #1, #2) |
| `panels_campaign_detail.py` | Campaign detail: Overview + Ad Groups tabs + Create Ad Group form | ✅ Built by designer (PR #1, #2 + create_ag added) |
| `panels_ui.py` | Shared helpers: formatters, badges, OAuth view, date helpers | Reusable, extend as needed |

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

### Right panel router (`panels_campaign.py`) — dispatches to:

**`panels_campaign_create.py`** (mode="create"):
- ui.Form: Name, Type (Select), Daily Budget, Bid Strategy (Select)
- Submit → create_campaign | Cancel → back to empty state

**`panels_campaign_detail.py`** (campaign_id present, mode not "create"/"create_ag"):
- Header: campaign name + status badge + ID + type
- Settings stats: budget / bidding strategy / status (3 columns)
- Tab selector: Overview button | Ad Groups (N) button (manual, not ui.Tabs)
- **Overview tab** (active_tab=0):
  - Period filter: 7D / 30D / This month
  - Spend vs Daily Budget bar chart (today_spend always 0 — per-campaign spend not in skeleton)
  - Period KPIs: Spend / Clicks / CTR / Avg CPC (from real report data, hidden if report fails)
  - Daily spend trend chart (from real report data, hidden if report fails)
- **Ad Groups tab** (active_tab=1):
  - List of ad groups with Keywords / Ads quick-action buttons → `ui.Call` (work without active chat)
  - "+ Ad Group" button → opens `mode="create_ag"` form inline in right panel
- Footer: Pause/Resume · AI Analyse → `ui.Call("analyze_performance")` (account-level AI analysis)

**`panels_campaign_detail.py`** — Create Ad Group form (mode="create_ag"):
- `ui.Form` with Name, Default CPC Bid, Language, hidden campaign_id
- Submit → `create_ad_group` | Cancel → back to Ad Groups tab

> ⚠️ **All buttons use `ui.Call`, not `ui.Send`.** `ui.Send` is currently a no-op from panels
> (platform GAP-B — `sendRef` not wired). See `docs/fix_ui_send_from_panel.md`.

---

## Design TODO

- [x] Right panel: Create campaign form (PR #1)
- [x] Right panel: Campaign detail — Overview tab with period filter + charts (PR #2)
- [x] Right panel: Ad Groups tab with list (PR #2)
- [x] Right panel: Create Ad Group inline form (mode="create_ag")
- [ ] Left panel: account dashboard — full redesign
- [ ] Left panel: not_connected view
- [ ] Left panel: account picker (multi-account)
- [ ] Left panel: needs_setup states
- [ ] Shared: review badge styles (Active/Paused/Deleted/Draft)
- [ ] Shared: review formatters (currency, percentage, number)

---

## Design Decisions

> Document design choices here as you make them.

---

## Open Questions

> Questions for SeeU — he'll answer in the PR or here.

---

## Notes

> Anything else worth remembering.
