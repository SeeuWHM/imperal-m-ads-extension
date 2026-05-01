# Microsoft Ads Extension — Full Documentation

**Version:** 1.2.0 | **Status:** Backend complete, frontend in design
**Extension ID:** `microsoft-ads` | **Tool:** `tool_msads_chat`
**Production:** `/opt/extensions/microsoft-ads/` on `whm-ai-worker`
**Git:** `github.com/SeeuWHM/imperal-m-ads-extension` | **SSH alias:** `github-m-ads`
**Latest commit:** `7142b97` (2026-05-01)

---

## Architecture

```
User (panel)
    ↓ ui.Open(oauth_url) — panel-driven, no chat required
Microsoft Login (Azure App c885090c, /common/ tenant)
    ↓ callback → Auth Gateway /v1/oauth/microsoft-ads/callback
    ↓ store: msads_accounts {access_token, refresh_token, display_name, _needs_setup=True}
Panel auto-setup: list_customers_for_token → activate → _needs_setup=False
    ↓ Extension → HTTP → whm-microsoft-ads-control (api-server:8090)
    X-Ms-Access-Token + X-Ms-Customer-Id + X-Ms-Account-Id headers
    ↓ BingAds SOAP SDK v13 → Microsoft Ads API
```

**OAuth flow:**
1. Panel renders Connect button with OAuth URL via `_build_oauth_url(ctx)` in `panels_ui.py`
2. `prompt=select_account` — forces fresh account selection
3. Auth Gateway callback stores tokens + display_name
4. Panel detects `_needs_setup=True` → calls `list_customers_for_token` → auto-activates
5. 1 account → auto-activate. Multiple accounts → show picker list.

---

## File Structure

```
microsoft-ads/
├── CLAUDE.md                        # Context for Claude (all collaborators)
├── docs/
│   ├── extension.md                 # This file — full technical docs
│   └── frontend.md                  # Frontend status (designer maintains)
├── main.py                          # Entry point + sys.modules isolation (all modules listed)
├── app.py                           # Extension v1.2.0 + ChatExtension + error helpers
│                                    # + MsadsDashboard (Pydantic cache model, @ext.cache_model)
├── handlers.py                      # connect, status, setup_account, switch_account, disconnect
├── handlers_campaigns.py            # list/get/create/update/pause/resume/delete campaign
├── handlers_ads.py                  # list/create/update ad_group, list/create/update ad
├── handlers_keywords.py             # list/add/pause/resume/delete keywords, research, bid_estimates
├── handlers_negative_keywords.py    # list/add/remove negative keywords
├── handlers_reports.py              # get_performance, get_search_terms, get_budget_status, analyze_performance
├── skeleton.py                      # @ext.skeleton("msads") → skeleton_refresh_msads
│                                    # @ext.tool skeleton_alert_msads
│                                    # _get_dashboard_data(ctx) → MsadsDashboard helper
├── panels.py                        # @ext.panel left: account dashboard (all states)
├── panels_campaign.py               # @ext.panel right: router — mode=create|detail, params routing
├── panels_campaign_create.py        # Create Campaign form (ui.Form with all campaign fields)
├── panels_campaign_detail.py        # Campaign detail: overview tab + ad groups tab
├── panels_ui.py                     # Shared helpers: formatters, OAuth URL, badges, date helpers
├── system_prompt.txt                # LLM system prompt
├── imperal.json                     # Manifest v1.2.0
└── msads_providers/
    ├── __init__.py
    ├── helpers.py                   # OAuth constants, _oauth_state, _all_accounts,
    │                                # _active_account, _MS_LOCATION_IDS, _to_location_ids()
    ├── token_refresh.py             # _refresh_msads_token, _refresh_token_if_needed
    └── msads_client.py              # HTTP client → whm-microsoft-ads-control
                                     # _get/_post/_patch/_delete helpers + all API methods
```

---

## 30 Chat Functions

### Account (`handlers.py`)
| Function | action_type | Description |
|----------|-------------|-------------|
| `connect` | read | OAuth URL. Checks if already connected. |
| `status` | read | Connection status + today's metrics from skeleton |
| `setup_account` | write | Post-OAuth: account discovery + activation |
| `switch_account` | write | Switch active account |
| `disconnect` | destructive | Remove account from store. Falls back to single account. |

### Campaigns (`handlers_campaigns.py`)
| Function | action_type | Description |
|----------|-------------|-------------|
| `list_campaigns` | read | List with budget/status/spend |
| `get_campaign` | read | Details + ad groups |
| `create_campaign` | write | Search/Shopping/Audience/DSA/PMax |
| `update_campaign` | write | Budget, status, bid strategy |
| `pause_campaign` | write | → Paused |
| `resume_campaign` | write | → Active |
| `delete_campaign` | destructive | Permanent deletion |

### Ad Groups + Ads (`handlers_ads.py`)
| Function | action_type | Description |
|----------|-------------|-------------|
| `list_ad_groups` | read | By campaign_id |
| `create_ad_group` | write | With cpc_bid + language |
| `list_ads` | read | By ad_group_id |
| `create_ad` | write | RSA: ≥3 headlines, ≥2 descriptions |
| `update_ad` | write | Replace headlines/descriptions/url |

### Keywords (`handlers_keywords.py`)
| Function | action_type | Description |
|----------|-------------|-------------|
| `list_keywords` | read | By ad_group_id, with quality score |
| `add_keywords` | write | Bulk: text + match_type + bid |
| `pause_keyword` | write | Requires keyword_id + ad_group_id |
| `resume_keyword` | write | Requires keyword_id + ad_group_id |
| `delete_keyword` | destructive | Permanent |
| `research_keywords` | read | AdInsight: seed keywords or URL |
| `get_bid_estimates` | read | MainLine1/MainLine/FirstPage positions |

### Negative Keywords (`handlers_negative_keywords.py`)
| Function | action_type | Description |
|----------|-------------|-------------|
| `list_negative_keywords` | read | Campaign or AdGroup level |
| `add_negative_keywords` | write | Phrase/Exact match |
| `remove_negative_keywords` | destructive | By keyword IDs |

### Reports (`handlers_reports.py`)
| Function | action_type | Description |
|----------|-------------|-------------|
| `get_performance` | read | campaign/ad-group/keyword/summary |
| `get_search_terms` | read | What users actually searched |
| `get_budget_status` | read | Today spend vs budget |
| `analyze_performance` | read | AI analysis via claude-sonnet-4-6. Optional `campaign_id` param to scope to one campaign. 3 reports fetched concurrently via `asyncio.gather`; partial failures degrade gracefully. |

---

## Store Structure

**Collection:** `msads_accounts` (one document per connected Microsoft Ads account per user)

```python
# Document fields stored in ext_store:
{
    "display_name":  str,   # "Web Host Most, LLC" or "Microsoft Ads User" (fallback)
    "provider":      str,   # always "microsoft-ads"
    "access_token":  str,   # OAuth access token (expires in ~1 hour)
    "refresh_token": str,   # OAuth refresh token (used to get new access_token)
    "expires_at":    int,   # Unix timestamp when access_token expires
    "customer_id":   str,   # Microsoft Ads customer ID (set by setup_account)
    "account_id":    str,   # Microsoft Ads account ID (set by setup_account)
    "account_name":  str,   # Account display name (set by setup_account)
    "currency":      str,   # e.g. "USD" (set by setup_account)
    "is_active":     bool,  # True = this is the active account for API calls
    "_needs_setup":  bool,  # True = OAuth done, account not selected yet
    "_needs_reauth": bool,  # True = refresh_token expired, user must re-auth
}
```

**Account states:**
- `_needs_setup=True`: OAuth completed, `customer_id`/`account_id` empty → panel shows account picker
- `_needs_setup=False, _needs_reauth=False`: fully active → API calls work
- `_needs_reauth=True`: refresh_token returned 400 → set by `token_refresh.py` → user must reconnect

**Token refresh logic (`msads_providers/token_refresh.py`):**
- `_refresh_token_if_needed(ctx, acc)`: refreshes if `expires_at < now + 120s` (2-minute buffer)
- Called automatically before every API call in `_get()/_post()/_patch()/_delete()`
- On 400 from Microsoft: sets `_needs_reauth=True` in store, returns acc unchanged
- On transient errors: logs warning, returns acc unchanged (does not fail the request)

---

## Skeleton + Panel Cache

**SDK pattern:** `@ext.skeleton("msads", ttl=300, alert=True)` (v1.6.0+)

| Tool registered as | SDK decorator | Section | TTL | Returns |
|-------------------|--------------|---------|-----|---------|
| `skeleton_refresh_msads` | `@ext.skeleton("msads")` | `msads` | 300s | `{"response": {connected, account_name, campaigns_active, campaigns_paused, alerts_count, today_spend, currency, error}}` |
| `skeleton_alert_msads` | `@ext.tool` | — | — | push notify if `budget_critical` (≥90%) |

**Data flow (`skeleton.py`):**
1. Kernel calls `skeleton_refresh_msads` on TTL schedule
2. `_get_dashboard_data(ctx)` → fetches `summary` report + `get_campaigns` from microservice
3. Returns `{"response": {scalar fields}}` — kernel persists to Redis as `msads` section for LLM classifier. Scalars only: connection state, account name, campaign counts, alert count, today's total spend.
4. **Side-effect:** writes full `MsadsDashboard` to `ctx.cache["dashboard"]` (TTL 300s) for panel use

**`_get_dashboard_data(ctx) -> MsadsDashboard`** — standalone helper in `skeleton.py`, imported by `panels.py` for cache-miss fallback:
- Fetches: `api.get_report(summary, today, aggregation=Summary)` + `api.get_campaigns()`
- Returns `MsadsDashboard(connected=False)` if account not ready
- Returns `MsadsDashboard(connected=True, error=...)` on API failure (panel shows warning)

**Panel cache model (`app.py`):**
```python
@ext.cache_model("msads_dashboard")
class MsadsDashboard(BaseModel):
    connected: bool          # False = no active account or not set up
    account_name: str        # "Web Host Most, LLC"
    account_id: str          # "187176890"
    currency: str            # "USD"
    today: dict              # spend, clicks, impressions, ctr, avg_cpc, conversions (account-level)
    campaigns: list          # top 10 from get_campaigns — metadata only (no per-campaign spend)
    campaigns_active: int
    campaigns_paused: int
    alerts: list             # budget_critical (≥90%) + budget_warning (≥70%)
    error: Optional[str]     # set on fetch failure, None on success
```

**`skeleton_alert_msads`** reads `ctx.cache["dashboard"]` — no additional API calls.

---

## Panels

### Left — `account_dashboard` (slot: left, file: `panels.py`)

Params: `disconnect`, `activate_id`, `doc_id`

| State | Condition |
|-------|-----------|
| `not_connected` | No accounts in store |
| `no_customers` | `_needs_setup=True`, 0 accounts found via API |
| `auto_setup` | `_needs_setup=True`, 1 account → auto-activate + refresh button |
| `picker` | `_needs_setup=True`, >1 accounts → `ui.List` account picker |
| `loading_error` | Account set up, cache empty + live fetch also failed |
| `dashboard` | `ctx.cache["dashboard"]` hit OR `ctx.cache.get_or_fetch()` succeeded |
| `disconnect="1"` | Wipes all store accounts → shows `not_connected` |

> **Panel data flow (v1.2.0):** `ctx.cache.get("dashboard", model=MsadsDashboard)` on every render. Cache hit (TTL 300s) = instant. Cache miss = `ctx.cache.get_or_fetch("dashboard", fetcher=_get_dashboard_data)` → live fetch + populates cache for next render.

### Right — `campaign_detail` (slot: right, router: `panels_campaign.py`)

Params: `campaign_id`, `mode`, `report_range` (default `LAST_7_DAYS`), `active_tab` (default 0)

| State | Condition | File |
|-------|-----------|------|
| Empty | No `campaign_id`, no `mode` | `panels_campaign.py` inline |
| Create campaign | `mode="create"` | `panels_campaign_create.py` |
| Create ad group | `mode="create_ag"` + `campaign_id` present | `panels_campaign_detail.py` → `_build_create_ag_view` |
| Campaign detail | `campaign_id` present, no special `mode` | `panels_campaign_detail.py` → `_build_detail_view` |

**Create campaign form** (`panels_campaign_create.py`):
- `ui.Form` with: Name (Input), Type (Select), Daily Budget (Input), Bid Strategy (Select)
- Submit → calls `create_campaign` handler
- Cancel → `ui.Call("__panel__campaign_detail", mode="", campaign_id="")` (clears state)

**Create ad group form** (`panels_campaign_detail.py` → `_build_create_ag_view`):
- `ui.Form` with: Name (Input), Default CPC Bid (Input), Language (Select), campaign_id (hidden)
- Submit → calls `create_ad_group` handler
- Cancel → `ui.Call("__panel__campaign_detail", campaign_id=..., active_tab=1, mode="view")`

**Campaign detail tabs** (`panels_campaign_detail.py` → `_build_detail_view`):
- Tab 0 **Overview**: period selector (7D/30D/This month) + spend vs budget bar chart + period KPIs + daily spend trend chart
- Tab 1 **Ad Groups (N)**: list with Keywords/Ads quick-action buttons + "+ Ad Group" button → `mode="create_ag"`

**Campaign detail footer actions:**
- Pause/Resume → `ui.Call("pause_campaign"/"resume_campaign", campaign_id=...)`
- AI Analyse → `ui.Call("analyze_performance", campaign_id=...)` — scoped to this campaign (`campaign_id` param added in v1.2.0)
- Keywords (per ad group) → `ui.Call("list_keywords", ad_group_id=...)`
- Ads (per ad group) → `ui.Call("list_ads", ad_group_id=...)`

> **Note (v1.1.1):** All panel buttons use `ui.Call` — `ui.Send` was replaced as it is a no-op in the current platform (GAP-B: `sendRef` not wired in `ExtensionPage.tsx`).

**Period report data:**
- Fetches `CampaignPerformanceReport` (Daily aggregation) for selected period via `api.get_report`
- If report fails (e.g. Basic Developer Token limitation) → degrades gracefully: shows budget chart only, period KPIs hidden
- `report_range` presets: `LAST_7_DAYS`, `LAST_30_DAYS`, `THIS_MONTH` (via `panels_ui.date_range()`)

---

## OAuth + Credentials

**Azure App:** `Imperal M-soft Ads` (client_id: `c885090c-cd0b-4074-8a12-58d05206ca36`)
- Redirect URI: `https://auth.imperal.io/v1/oauth/microsoft-ads/callback`
- Tenant: `/common/` — supports personal MSA + work accounts
- Scope: `https://ads.microsoft.com/msads.manage offline_access`
- Secrets valid until: 2028-04

**Auth Gateway:** `/v1/oauth/microsoft-ads/callback`
- Saves: `access_token`, `refresh_token`, `display_name`, `_needs_setup=True`
- display_name falls back to "Microsoft Ads User" (MS Ads token lacks Graph scope)

---

## Microservice (whm-microsoft-ads-control)

**URL:** `https://api.webhostmost.com/microsoft-ads` (api-server:8090)

Multi-tenant via headers: `X-Ms-Access-Token` + `X-Ms-Customer-Id` + `X-Ms-Account-Id`
→ middleware routes to `UserMicrosoftAdsClient` using user's token.

**Dual client_id architecture:**
- `dd2bfaf0` — WHM singleton (owns the refresh_token)
- `c885090c` — Extension users OAuth app

**⚠️ CRITICAL LIMITATION: Basic Developer Token**
- Token `145Q3WA7EH570141` works ONLY with the `webhostmost@outlook.com` account
- Other users → `Invalid client data` SOAP fault on all API calls (campaign/keyword/report operations)
- The multi-tenant middleware (`UserMicrosoftAdsClient`) and scope fixes are in place — they will work correctly once Universal Developer Token is approved
- Fix: apply for Universal Developer Token at [Microsoft Advertising Developer Portal](https://developers.ads.microsoft.com/)

---

## Deploy

**Only via Developer Portal** (git → deploy). Never via MCP write_file.

```bash
# From /Imperal-Extensions-MCP/SeeU-Extensions/microsoft-ads/
git add <files>
git commit -m "..."
git push origin main   # SSH alias: github-m-ads

# Developer Portal: Deploy tab → select latest commit
# Then: imperal-platform-worker@{1..3} restart needed for new code
```

---

## panels_ui.py — Shared Helpers Reference

| Function/Constant | Description |
|------------------|-------------|
| `fmt_currency(amount, currency)` | `"$1.23"` — currency symbol + 2 decimal places |
| `fmt_pct(value, decimals=1)` | `"3.2%"` — percentage with configurable decimals |
| `fmt_number(value)` | `"1,204"` — integer with thousands separator |
| `campaign_badge(status)` | Returns `ui.Badge` with color: Active=green, Paused=gray, Deleted=red, Draft=yellow |
| `not_connected_view(ctx)` | Full not-connected state UI with OAuth Connect button |
| `error_view(msg, ctx)` | Error state UI with Reconnect button |
| `_build_oauth_url(ctx)` | Builds the full OAuth URL with state, prompt=select_account |
| `DATE_OPTS` | List of date range preset dicts for use in `ui.Select` |
| `date_range(preset)` | Converts preset string → `(start_date, end_date)` ISO tuple |

**Date presets in `DATE_OPTS`:**
- `"TODAY"` → today / today
- `"LAST_7_DAYS"` → 6 days ago / today
- `"LAST_30_DAYS"` → 29 days ago / today
- `"THIS_MONTH"` → 1st of month / today
- `"LAST_MONTH"` → 1st of prev month / last day of prev month

---

## Health Check

`app.py` registers `@ext.health_check` that returns:
```python
{
    "status":             "ok" | "degraded",
    "version":            "1.2.0",
    "accounts_connected": int,
    "oauth_configured":   bool,
    "microservice":       "ok" | "degraded" | "unreachable",
}
```

---

## Known Issues

- [ ] **Universal Developer Token** — multi-user blocked until Microsoft approves application. Extension + microservice are architecturally ready (multi-tenant OAuth, proper scope routing), but all SOAP calls fail for non-WHM accounts with Basic token.
- [ ] **display_name = "Microsoft Ads User"** — MS Ads token doesn't have Graph `User.Read` scope; OAuth `display_name` is always "Microsoft Ads User" unless MS Graph scope added.
- [ ] **CampaignPerformanceReport → 502 for non-WHM users** — Basic Developer Token limitation; `get_budget_status` degrades gracefully (shows budget without live spend).
- [ ] **ui.Send from panel buttons is silent** — platform GAP, see `docs/fix_ui_send_from_panel.md`. Currently worked around with `ui.Call` for all panel actions.
- [x] ~~**`analyze_performance` → 502 SOAP fault**~~ — Fixed 2026-04-27 in microservice: `TimePeriod` column stripped for `Summary` aggregation in `get_campaign_performance` + `get_keyword_performance` + `get_search_query_performance`
- [x] ~~**`list_keywords` / `list_ads` → HTTP 500**~~ — Fixed 2026-04-27 in microservice: added try/except to `keywords/router.py` and `ads/router.py`; SOAP errors now return 502 with descriptive message
- [x] ~~**Report scope uses WHM account for user clients**~~ — Fixed 2026-04-27 in microservice: `_build_account_scope` + `_build_ad_group_scope` now use `self._authorization_data.account_id`
- [x] ~~**Panel always makes live API calls on every render**~~ — Fixed 2026-04-27 in extension: panels now use `ctx.cache.get_or_fetch()` with 300s TTL; `skeleton_alert` reads from cache instead of live fetch
- [x] ~~**`skeleton_refresh_msads` uses `@ext.tool` instead of `@ext.skeleton`**~~ — Fixed 2026-04-27: now `@ext.skeleton("msads", ttl=300, alert=True)`, returns `ActionResult.success`, writes `MsadsDashboard` to `ctx.cache`
- [x] ~~**`fn_status` today metrics**~~ — `ctx.skeleton` forbidden in `@chat.function` (SDK v1.6.0); `today` returns `{}`
- [x] ~~**`skeleton_alert_msads` + panels skeleton reads**~~ — superseded by v1.2.0 `ctx.cache` pattern

---

> See [CHANGELOG.md](../CHANGELOG.md) for full version history.
