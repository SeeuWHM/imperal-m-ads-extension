# Microsoft Ads Extension — Full Documentation

**Version:** 1.1.0 | **Status:** Backend complete, frontend in design
**Extension ID:** `microsoft-ads` | **Tool:** `tool_msads_chat`
**Production:** `/opt/extensions/microsoft-ads/` on `whm-ai-worker`
**Git:** `github.com/SeeuWHM/imperal-m-ads-extension` | **SSH alias:** `github-m-ads`
**Latest commit:** `e2f18f1`

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
├── main.py                          # Entry point + sys.modules isolation
├── app.py                           # Extension + ChatExtension(haiku) + error helpers
├── handlers.py                      # connect, status, setup_account, switch_account, disconnect
├── handlers_campaigns.py            # list/get/create/update/pause/resume/delete campaign
├── handlers_ads.py                  # list/create ad_group, list/create/update ad
├── handlers_keywords.py             # list/add/pause/resume/delete keywords, research, bid_estimates
├── handlers_negative_keywords.py    # list/add/remove negative keywords
├── handlers_reports.py              # get_performance, get_search_terms, get_budget_status, analyze_performance
├── skeleton.py                      # skeleton_refresh_msads + skeleton_alert_msads
├── panels.py                        # @ext.panel left: account dashboard (all states)
├── panels_campaign.py               # @ext.panel right: campaign detail + ad groups
├── panels_ui.py                     # shared helpers: formatters, OAuth URL, badges
├── system_prompt.txt                # LLM system prompt
├── imperal.json                     # Manifest v1.1.0
└── msads_providers/
    ├── __init__.py
    ├── helpers.py                   # OAuth constants, _oauth_state, _all_accounts,
    │                                # _active_account, _MS_LOCATION_IDS, _to_location_ids()
    ├── token_refresh.py             # _refresh_msads_token, _refresh_token_if_needed
    └── msads_client.py              # HTTP client → whm-microsoft-ads-control
                                     # _get/_post/_patch/_delete helpers
                                     # All API methods
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
| `analyze_performance` | read | AI analysis via claude-sonnet-4-6 |

---

## Skeleton

| Tool | Section | TTL | Returns |
|------|---------|-----|---------|
| `skeleton_refresh_msads` | `msads_account` | 300s | account info + today KPIs + campaigns + alerts |
| `skeleton_alert_msads` | — | — | push notify if budget_critical (≥90%) |

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
- Token `145Q3WA7EH570141` works ONLY with `webhostmost@outlook.com`
- Other users → `Invalid client data` SOAP fault on API calls
- Fix: apply for Universal Developer Token at Microsoft Advertising Developer Portal

---

## Deploy

**Only via Developer Portal** (git → deploy). Never via MCP write_file.

```bash
# SeeU's push flow (local .git broken by Nextcloud sync):
cp -r <files> /tmp/ms-ads-push/
cd /tmp/ms-ads-push
git add -A && git commit -m "..."
git push origin main

# Developer Portal: Deploy tab → select latest commit
# Then: imperal-platform-worker@{1..3} restart needed for new code
```

---

## Known Issues

- [ ] **Universal Developer Token** — multi-user blocked until Microsoft approves application
- [ ] **display_name = "Microsoft Ads User"** — MS Ads token doesn't have Graph `User.Read` scope
- [ ] **CampaignPerformanceReport → 502** — Basic token limitation on reporting API; `get_budget_status` gracefully falls back to campaign list without live spend

---

## Changelog

### v1.1.0 (2026-04-23)
- Fixed: `fn_get_budget_status` — replaced non-existent `/v1/reports/budget` with parallel campaign fetch
- Fixed: `create_campaign/ad_group/ad` — ID extraction from nested `{"campaign": {...}}` response
- Fixed: `panels_campaign` — ad groups tab was always empty (missing parallel `get_ad_groups` call)
- Fixed: Account activation — `is_active: True` now set on all 3 activation paths
- Fixed: `AccountParams.account` — added `default=""` to prevent ValidationError on disconnect
- Fixed: `get_report` — `campaign_id` → `campaign_ids` (comma-sep string) for campaign report endpoint
- Fixed: `research_keywords` + `get_bid_estimates` — `location` string → `location_ids` list via mapping
- Fixed: `add_keywords` — `keyword_ids` extracted from `result["keywords"]`
- Fixed: `fn_get_campaign` — removed double-nesting in ActionResult data
- Fixed: `create_ad/update_ad` — headlines/descriptions converted to HeadlineAsset dicts, `final_url` → `final_urls` list, `ad_group_id` moved to query param
- New: `pause_keyword`, `resume_keyword`, `delete_keyword`
- New: `delete_campaign`
- New: `list_negative_keywords`, `add_negative_keywords`, `remove_negative_keywords`
- New: `handlers_negative_keywords.py` module
