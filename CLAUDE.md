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
panels.py           — LEFT panel: account dashboard (all states)
panels_campaign.py  — RIGHT panel: campaign detail + ad groups
panels_ui.py        — shared helpers: formatters, OAuth URL, badges
docs/frontend.md    — your working notes, status, decisions (you maintain this)
```

**Do NOT touch** — backend is complete and working:
```
handlers*.py        — 30 chat functions
msads_providers/    — API client, token refresh, helpers
skeleton.py         — background data refresh
main.py             — entry point
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

## Data available in panels

### Left panel — `panels.py`

Panel receives data from `ctx.skeleton.get("msads_account")`. Read `skeleton.py` to see
exactly what's returned. Key fields:

```python
# Account
data["account_name"]        # str  — e.g. "Web Host Most, LLC"
data["account_id"]          # str  — e.g. "187176890"
data["currency"]            # str  — e.g. "USD"

# Today's KPIs
data["today"]["spend"]      # float — total spend today
data["today"]["clicks"]     # int
data["today"]["impressions"]# int
data["today"]["ctr"]        # float — e.g. 3.2 (percent)
data["today"]["avg_cpc"]    # float
data["today"]["conversions"]# float

# Campaigns (top 10 from skeleton)
data["campaigns"]           # list of dicts:
  # c["id"]                 — campaign ID
  # c["name"]               — campaign name
  # c["status"]             — "Active" | "Paused"
  # c["daily_budget"]       — float
  # c["today_spend"]        — float (may be 0 if reports unavailable)
  # c["clicks"]             — int

data["campaigns_active"]    # int
data["campaigns_paused"]    # int

# Budget alerts
data["alerts"]              # list:
  # a["type"]               — "budget_critical" | "budget_warning"
  # a["campaign_name"]      — str
  # a["pct_used"]           — float (e.g. 94.2)
```

**Panel states you must handle:**

| State | When | What to show |
|-------|------|-------------|
| `not_connected` | No accounts in store | Connect button with OAuth URL |
| `needs_setup` (1 account auto-selected) | `_needs_setup=True`, 1 customer found | Success message + refresh button |
| `needs_setup` (multi-account) | `_needs_setup=True`, multiple customers | Account picker list |
| `no_customers` | `_needs_setup=True`, 0 customers | Warning + "Try different account" |
| `loading_error` | Account set up but skeleton empty | Warning + retry button |
| `dashboard` | Skeleton loaded | Full dashboard |
| `disconnect="1"` param | User clicked disconnect | Delete all accounts → show not_connected |

### Right panel — `panels_campaign.py`

Receives `campaign_id` param when user clicks a campaign in the left panel.
Panel fetches data in parallel (already wired in `panels_campaign.py`):

```python
# From api.get_campaign():
campaign["name"]             # str
campaign["status"]           # "Active" | "Paused"
campaign["daily_budget"]     # float
campaign["campaign_type"]    # "Search" | "Shopping" | "Audience" | "DynamicSearchAds" | "PerformanceMax"
campaign["bidding_scheme"]   # "MaxClicks" | "MaxConversions" | "EnhancedCpc" | "ManualCpc" | ...

# From api.get_ad_groups():
ad_groups                    # list:
  # ag["id"] / ag["ad_group_id"]
  # ag["name"]
  # ag["cpc_bid"]            — float
  # ag["status"]             — "Active" | "Paused"
  # ag["language"]           — "English" | ...

# From skeleton (this campaign's today data):
today_spend                  # float — spend today for THIS campaign
today_clicks                 # int
today_ctr                    # float
today_cpc                    # float
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

## Git workflow — all allowed commands

You work in **feature branches only**. Never push directly to `main`.

### Setup (first time)
```bash
git clone git@github.com:SeeuWHM/imperal-m-ads-extension.git
cd imperal-m-ads-extension
```

### Daily workflow
```bash
# See current state
git status
git diff

# Create a feature branch
git checkout -b ui/account-dashboard
git checkout -b ui/campaign-detail
git checkout -b ui/design-tokens

# Stage your files (only panel files + docs)
git add panels.py panels_campaign.py panels_ui.py
git add docs/frontend.md

# Commit
git commit -m "ui: redesign account dashboard with budget progress bar"
git commit -m "ui: campaign detail tabs — Today and Ad Groups"
git commit -m "docs: update frontend status"

# Push your branch
git push origin ui/account-dashboard

# View history
git log --oneline -10

# Switch between branches
git checkout main
git checkout ui/account-dashboard

# Get latest from main
git fetch origin
git merge origin/main

# See all branches
git branch -a
```

### Commit message format
```
ui: <what you changed>          — panel/design changes
docs: <what you documented>     — frontend.md updates
fix: <what you fixed>           — bug in panel logic
```

### After push
Open a Pull Request on GitHub → `ui/<your-branch>` → `main`.
SeeU reviews and merges. SeeU deploys via Developer Portal.

**You never run:** `git push origin main` · `systemctl` · any server commands.

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
