# Microsoft Ads Extension — Imperal Cloud

**Extension ID:** `microsoft-ads` | **Version:** 1.1.0
**Platform:** [panel.imperal.io](https://panel.imperal.io) | **Repo:** `github.com/SeeuWHM/imperal-m-ads-extension`

---

## What this is

An AI-powered Microsoft Advertising manager. Users connect their Microsoft Ads account via OAuth
in the panel and manage campaigns, keywords, budgets, and ads through natural language chat.

**User journey:**
1. Open the Microsoft Ads panel → click "Connect" → Microsoft OAuth login
2. Panel auto-detects the ad account and activates it
3. Dashboard shows today's spend, clicks, CTR, budget bar, campaign list
4. User clicks a campaign → right panel shows details, ad groups, today's chart
5. User types in chat → AI calls backend functions → results shown in chat + panels refresh

---

## Your files (frontend only)

```
panels.py                — LEFT panel: account dashboard (all states)
panels_campaign.py       — RIGHT panel: router (dispatches by mode param)
panels_campaign_create.py — Create campaign form (ui.Form)
panels_campaign_detail.py — Campaign detail: Overview + Ad Groups tabs
panels_ui.py             — shared helpers: formatters, OAuth URL, badges, date helpers
docs/frontend.md         — your working notes, status, decisions (you maintain this)
```

**Do NOT touch** — backend is complete and working:
```
handlers*.py        — 30 chat functions
msads_providers/    — API client, token refresh, helpers
skeleton.py         — background data refresh
main.py             — entry point (add new panel files here if you split further)
app.py              — extension setup
imperal.json        — manifest
system_prompt.txt   — LLM instructions
```

---

## SDK Documentation

Read these directly when you need them — always up-to-date:

| What | URL |
|------|-----|
| All UI components (57) with examples | https://github.com/imperalcloud/imperal-sdk/blob/main/docs/ui-components.md |
| Panel layout (3-column, slots, spacing) | https://github.com/imperalcloud/imperal-sdk/blob/main/docs/extension-ui.md |
| Extension rules (V1–V19, semantic styling) | https://github.com/imperalcloud/imperal-sdk/blob/main/docs/extension-guidelines.md |

**Key components you'll use most:**
`ui.Stack`, `ui.Header`, `ui.Stats` + `ui.Stat`, `ui.List` + `ui.ListItem`,
`ui.Button`, `ui.Badge`, `ui.Alert`, `ui.Progress`, `ui.Chart`, `ui.Tabs`,
`ui.Text`, `ui.Divider`, `ui.Empty`

---

## Helpers available in `panels_ui.py`

These are already implemented — import and use them, don't re-implement:

```python
from panels_ui import (
    fmt_currency,    # fmt_currency(1234.5, "USD") → "$1234.50"
    fmt_pct,         # fmt_pct(3.256) → "3.3%"  (1 decimal default)
    fmt_number,      # fmt_number(1204) → "1,204"
    campaign_badge,  # campaign_badge("Active") → ui.Badge(green)
                     # campaign_badge("Paused") → ui.Badge(gray)
                     # campaign_badge("Deleted") → ui.Badge(red)
    not_connected_view,  # full not-connected UI state
    error_view,          # error UI with reconnect button
    DATE_OPTS,       # list of date range presets for ui.Select
    date_range,      # date_range("LAST_7_DAYS") → ("2026-04-17", "2026-04-24")
)
```

**`DATE_OPTS`** — use in a date range picker:
```python
DATE_OPTS = [
    {"value": "TODAY",        "label": "Today"},
    {"value": "LAST_7_DAYS",  "label": "Last 7 days"},
    {"value": "LAST_30_DAYS", "label": "Last 30 days"},
    {"value": "THIS_MONTH",   "label": "This month"},
    {"value": "LAST_MONTH",   "label": "Last month"},
]
```

---

## Data available in panels

### Left panel — `panels.py`

Panel receives data from **`ctx.cache.get("dashboard", model=MsadsDashboard)`** (v1.2.0+).
On cache miss → `ctx.cache.get_or_fetch("dashboard", fetcher=_get_dashboard_data)`.
The cache is populated by `skeleton_refresh_msads` every 300s and on any panel cold-start.
Read `skeleton.py` (`_get_dashboard_data`) and `app.py` (`MsadsDashboard`) for the full model.

Key fields (`data = cached.model_dump()`):

```python
# Account
data["account_name"]        # str  — e.g. "Web Host Most, LLC"
data["account_id"]          # str  — e.g. "187176890"
data["currency"]            # str  — e.g. "USD"

# Account-level today's KPIs (from AccountPerformanceReport)
data["today"]["spend"]      # float — TOTAL account spend today (real, from report)
data["today"]["clicks"]     # int   — TOTAL account clicks today
data["today"]["impressions"]# int
data["today"]["ctr"]        # float — e.g. 3.2 (shown as percent)
data["today"]["avg_cpc"]    # float
data["today"]["conversions"]# float

# ⚠️ IMPORTANT — these may be 0 if AccountPerformanceReport had no data yet today
# All six fields default to 0 when skeleton first loads or report is empty.

# Campaigns list — top 10 (from GET /v1/campaigns — NOT a performance report)
data["campaigns"]           # list of campaign dicts:
  # c["id"]                 — int, campaign ID (use this for all calls)
  # c["name"]               — str
  # c["status"]             — "Active" | "Paused" | "Deleted" | None
  # c["campaign_type"]      — "Search" | "Shopping" | "Audience" | "DynamicSearchAds" | "PerformanceMax" | None
  # c["daily_budget"]       — float | None
  # c["bidding_scheme"]     — "MaxClicks" | "MaxConversions" | "EnhancedCpc" | "ManualCpc" | None
  # c["budget_type"]        — "DailyBudgetStandard" | "DailyBudgetAccelerated" | None
  # c["start_date"]         — "YYYY-MM-DD" | None
  # c["end_date"]           — "YYYY-MM-DD" | None

# ⚠️ CRITICAL — campaigns do NOT have per-campaign spend/clicks from the skeleton.
# today_spend, clicks, ctr are NOT fields in the campaign dict.
# They will always be 0 when read from the campaigns list.
# The ONLY real per-day spend is data["today"]["spend"] (account total).
# Do NOT build per-campaign spend bars in the left panel — they will always show 0.
# If you want per-campaign spend, it requires a separate API call (get_budget_status).

data["campaigns_active"]    # int — count of Active campaigns
data["campaigns_paused"]    # int — count of Paused campaigns

# Budget alerts (only present when spend ≥ 70% of daily budget)
data["alerts"]              # list:
  # a["type"]               — "budget_critical" (≥90%) | "budget_warning" (≥70%)
  # a["campaign_name"]      — str
  # a["pct_used"]           — float (e.g. 94.2)
  # a["campaign_id"]        — str (only in "budget_critical", NOT in "budget_warning")
```

**Panel states you must handle:**

| State | When | What to show |
|-------|------|-------------|
| `not_connected` | No accounts in store | Connect button with OAuth URL |
| `needs_setup` (1 account auto-selected) | `_needs_setup=True`, 1 customer found | Success message + refresh button |
| `needs_setup` (multi-account) | `_needs_setup=True`, multiple customers | Account picker list |
| `no_customers` | `_needs_setup=True`, 0 customers | Warning + "Try different account" |
| `loading_error` | Account set up, cache empty, live fetch also failed | Warning + retry button |
| `dashboard` | Cache hit (`ctx.cache`) or live fetch succeeded | Full dashboard |
| `disconnect="1"` param | User clicked disconnect | Delete all accounts → show not_connected |

### Right panel — `panels_campaign.py` (router) + `panels_campaign_detail.py` (detail)

The right panel is a router. Params: `campaign_id`, `mode`, `report_range`, `active_tab`.
- `mode="create"` → shows `panels_campaign_create.py` (Create Campaign form)
- `campaign_id` present → shows `panels_campaign_detail.py` (campaign detail)
- No params → empty state

**`panels_campaign_detail.py`** fetches data in parallel:

```python
# From api.get_campaign() → {"campaign": {...}}  (unwrapped in panel code)
campaign["id"]               # int
campaign["name"]             # str
campaign["status"]           # "Active" | "Paused" | "Deleted" | None
campaign["daily_budget"]     # float | None
campaign["campaign_type"]    # "Search" | "Shopping" | "Audience" | "DynamicSearchAds" | "PerformanceMax" | None
campaign["bidding_scheme"]   # "MaxClicks" | "MaxConversions" | "MaxConversionValue" | "EnhancedCpc" | "ManualCpc" | None
campaign["budget_type"]      # "DailyBudgetStandard" | "DailyBudgetAccelerated" | None
campaign["start_date"]       # "YYYY-MM-DD" | None
campaign["end_date"]         # "YYYY-MM-DD" | None
campaign["languages"]        # list[str] | None — e.g. ["English", "French"] or ["All"]
campaign["tracking_url_template"]  # str | None
campaign["final_url_suffix"] # str | None

# From api.get_ad_groups() → {"ad_groups": [...]}
ad_groups                    # list:
  # ag["id"]                 — int, ad group ID
  # ag["campaign_id"]        — int | None
  # ag["name"]               — str
  # ag["status"]             — "Active" | "Paused" | None
  # ag["ad_group_type"]      — "SearchStandard" | "SearchDynamic" | None
  # ag["cpc_bid"]            — float | None (default CPC bid)
  # ag["cpm_bid"]            — float | None (for Audience campaigns)
  # ag["language"]           — "English" | "Spanish" | ... | None
  # ag["network"]            — str | None
  # ag["inherited_bidding_scheme"] — str | None (read-only, from campaign)

# From api.get_report() → period CampaignPerformanceReport (Daily aggregation)
# report_data["rows"] — list of daily rows for the selected period:
#   r["TimePeriod"]  — "YYYY-MM-DD"
#   r["Spend"]       — float (spend for that day)
#   r["Clicks"]      — int
#   r["Impressions"] — int
#   r["Ctr"]         — float (percent)
#   r["AverageCpc"]  — float
#
# ⚠️ report_data may be {} if CampaignPerformanceReport fails (Basic token limitation)
# In that case panels_campaign_detail.py shows budget chart only — period KPIs hidden.
# The code handles this gracefully — do NOT add error states for empty report_data.

# ⚠️ today_spend from cache campaigns is still always 0 (campaigns list has no
# per-campaign spend data). today_spend in panels_campaign_detail.py will show 0.
# The period spend in Overview tab comes from report_data (real data from CampaignPerformanceReport).
```

**Panel states:**

| State | When |
|-------|------|
| Empty | No `campaign_id` param — "Select a campaign from the left panel" |
| Error | API call failed — show error + retry button |
| Loaded | Show header, settings, tabs |

**Tabs:** "Today" (spend chart + KPIs) · "Ad Groups (N)" (list with actions)

---

## Triggering actions from panels

Panels call backend functions using `ui.Call()` and `ui.Send()`:

```python
# Call a panel function (stays in panel, no chat)
ui.Call("__panel__account_dashboard", disconnect="1")
ui.Call("__panel__campaign_detail", campaign_id=cid)

# Call a chat function (writes to chat)
ui.Call("pause_campaign", campaign_id=cid)    # direct function call
ui.Send("Create a new Microsoft Ads campaign") # sends as user message

# Open external URL
ui.Open(url)   # for OAuth button
```

---

## Git workflow — step by step, no exceptions

> Follow this exactly. If something looks different from what's described — stop and ask SeeU.

---

### First time setup

```bash
# 1. Add the SSH key (SeeU gave you a file called denchik_msads_ed25519)
mkdir -p ~/.ssh
cp denchik_msads_ed25519 ~/.ssh/denchik_msads_ed25519
chmod 600 ~/.ssh/denchik_msads_ed25519

# 2. Tell SSH to use this key for GitHub
cat >> ~/.ssh/config << 'EOF'
Host github-msads
  HostName github.com
  User git
  IdentityFile ~/.ssh/denchik_msads_ed25519
EOF

# 3. Clone the repo
git clone git@github-msads:SeeuWHM/imperal-m-ads-extension.git
cd imperal-m-ads-extension
```

---

### Every time you start working

```bash
# Step 1 — always check where you are
git status
git branch          # must show you're on a branch like ui/something, NOT main

# Step 2 — get the latest from SeeU
git fetch origin
git merge origin/main   # only if you're on your feature branch
```

---

### Starting work on something new

```bash
# ALWAYS create a branch before changing any file
# Branch name format: ui/<what-you-are-building>
git checkout -b ui/account-dashboard
git checkout -b ui/campaign-detail
git checkout -b ui/not-connected-view
git checkout -b ui/badges-and-formatters

# Verify you are on the new branch (not main!)
git branch
# Should show:  * ui/account-dashboard
```

---

### Saving your work (commit)

```bash
# Step 1 — check what you changed
git status
git diff

# Step 2 — add ONLY your files (copy these exact commands)
git add panels.py
git add panels_campaign.py
git add panels_ui.py
git add docs/frontend.md

# NEVER run: git add .
# NEVER run: git add -A
# NEVER run: git add handlers.py or any handlers_*.py file
# NEVER run: git add main.py
# NEVER run: git add app.py
# NEVER run: git add imperal.json
# NEVER run: git add system_prompt.txt
# NEVER run: git add msads_providers/

# Step 3 — verify only your files are staged
git status
# Should only show panels.py, panels_campaign.py, panels_ui.py, docs/frontend.md

# Step 4 — syntax check before committing
python3 -m py_compile panels.py
python3 -m py_compile panels_campaign.py
python3 -m py_compile panels_ui.py
# If any of these prints an error — fix it before committing

# Step 5 — commit with a clear message
git commit -m "ui: redesign account dashboard — budget progress bar + KPI stats"
git commit -m "ui: campaign detail — Today tab with spend chart"
git commit -m "ui: not-connected view — connect button with icon"
git commit -m "docs: update frontend status and design decisions"
```

**Commit message format:**
```
ui: <what you built or changed>    ← for panel changes
docs: <what you documented>        ← for frontend.md only
fix: <what you fixed>              ← for bug fixes in panels
```

---

### Sending your work to SeeU (push)

```bash
# Step 1 — verify you are NOT on main
git branch
# Must show: * ui/your-branch-name
# If it shows: * main — STOP. Do not push. Create a branch first.

# Step 2 — push your branch
git push origin ui/account-dashboard   # use your actual branch name

# Step 3 — open a Pull Request
# Go to: https://github.com/SeeuWHM/imperal-m-ads-extension
# Click "Compare & pull request"
# Base: main ← Compare: ui/your-branch
# Add a description of what you changed
# Click "Create pull request"
```

SeeU will review, merge, and deploy. You don't need to do anything after the PR.

---

### Useful commands

```bash
git log --oneline -10    # see last 10 commits
git diff                 # see what you changed (not yet staged)
git diff --cached        # see what is staged for commit
git branch -a            # see all branches
git stash                # temporarily save work without committing
git stash pop            # bring it back
```

---

### ⛔ Commands you must NEVER run

```bash
git push origin main          # NEVER — SeeU merges to main, not you
git push --force              # NEVER
git reset --hard              # NEVER — destroys your work
git checkout -- .             # NEVER — destroys your changes
git add .                     # NEVER — might accidentally stage backend files
git add -A                    # NEVER — same reason
```

---

### If something went wrong

```bash
# See what happened
git status
git log --oneline -5

# Undo last commit (keeps your changes, just undoes the commit)
git reset HEAD~1

# If you accidentally staged wrong files — unstage them
git restore --staged handlers.py
git restore --staged main.py
```

If you're not sure what to do — **stop and ask SeeU** before running anything.

---

## Rules

1. **Only `ui.*` components** — everything in the [SDK docs](https://github.com/imperalcloud/imperal-sdk/blob/main/docs/ui-components.md). No raw HTML, no custom CSS.
2. **No business logic in panels** — panels read data and render UI. Logic lives in `handlers_*.py`.
3. **Syntax check before every commit:** `python3 -m py_compile panels.py panels_campaign.py panels_ui.py`
4. **Read the existing code first** — `panels.py` and `panels_campaign.py` have working implementations. Understand what's there before changing.
5. **Update `docs/frontend.md`** as you work — what you've done, decisions made, open questions.
6. **300 lines max per file** — if panels.py grows beyond 300 lines, split into submodules.

---

## Understanding the current panels

Before building, read the existing files in this order:
1. `panels_ui.py` — helpers and formatters you can reuse
2. `panels.py` — left panel, all 7 states already wired
3. `panels_campaign.py` — right panel, tabs already built

The backend is **fully working**. The panels are functional but designed by a developer, not a designer.
Your job: make them look great using the Imperal design system.

---

## Working notes → `docs/frontend.md`

That file is yours. Update it as you go:
- What's been redesigned
- Design decisions
- Open questions for SeeU
- What's next
