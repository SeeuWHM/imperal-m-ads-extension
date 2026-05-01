# imperal-m-ads-extension

[![Imperal SDK](https://img.shields.io/badge/imperal--sdk-3.5.x-blue)](https://pypi.org/project/imperal-sdk/)
[![Version](https://img.shields.io/badge/version-1.2.0-green)](https://github.com/SeeuWHM/imperal-m-ads-extension/releases)
[![Platform](https://img.shields.io/badge/platform-Imperal%20Cloud-purple)](https://panel.imperal.io)

**Microsoft Advertising AI manager extension for [Imperal Cloud](https://panel.imperal.io).**

Connect your Microsoft Ads account via OAuth and manage campaigns, ad groups, keywords,
negative keywords, and performance reports through natural language.

---

## What It Does

Talk to it naturally:

```
"show me all campaigns"
"pause the Summer Sale campaign"
"create a Search campaign with $50 daily budget"
"add negative keywords: free, tutorial, cheap"
"what keywords have the lowest quality score?"
"pause keyword 123456 in ad group 789"
"give me performance for last 7 days"
"research keywords for cloud hosting"
"analyze my campaign performance and give recommendations"
```

Or manage from the panel — left sidebar shows account KPIs, budget bar, and campaign list;
right panel shows campaign detail, ad groups, and today's performance.

---

## Capabilities

### Account Management
| Function | Description |
|----------|-------------|
| `connect` | OAuth2 via Microsoft Azure (Azure App `c885090c`) |
| `status` | Current account info + today's KPIs from skeleton |
| `setup_account` | Post-OAuth: discover and activate an ad account |
| `switch_account` | Switch between multiple connected accounts |
| `disconnect` | Remove account credentials from store |

### Campaigns
| Function | Description |
|----------|-------------|
| `list_campaigns` | All campaigns with budget and status |
| `get_campaign` | Campaign detail + ad groups |
| `create_campaign` | Search / Shopping / Audience / DSA / PerformanceMax |
| `update_campaign` | Budget, status, bid strategy, tracking |
| `pause_campaign` | Set status → Paused |
| `resume_campaign` | Set status → Active |
| `delete_campaign` | Permanently delete a campaign |

### Ad Groups & Ads
| Function | Description |
|----------|-------------|
| `list_ad_groups` | Ad groups by campaign ID |
| `create_ad_group` | With language, CPC bid, network |
| `list_ads` | Ads by ad group ID |
| `create_ad` | RSA: ≥3 headlines (max 30 chars), ≥2 descriptions (max 90 chars) |
| `update_ad` | Replace headlines / descriptions / final_urls |

### Keywords
| Function | Description |
|----------|-------------|
| `list_keywords` | By ad group — text, match type, bid, quality score |
| `add_keywords` | Bulk: text + match_type (Broad/Phrase/Exact) + optional bid |
| `pause_keyword` | Pause — requires keyword_id + ad_group_id |
| `resume_keyword` | Resume — requires keyword_id + ad_group_id |
| `delete_keyword` | Permanently delete |
| `research_keywords` | AdInsight: keyword ideas from seed keywords or URL |
| `get_bid_estimates` | Bid needed for MainLine1 / MainLine / FirstPage positions |

### Negative Keywords
| Function | Description |
|----------|-------------|
| `list_negative_keywords` | List by campaign ID or ad group ID |
| `add_negative_keywords` | Add Phrase/Exact negatives at Campaign or AdGroup level |
| `remove_negative_keywords` | Delete by negative keyword IDs |

### Reports & AI Analysis
| Function | Description |
|----------|-------------|
| `get_performance` | Campaign / ad-group / keyword / summary, any date range |
| `get_search_terms` | Actual search queries triggering your ads |
| `get_budget_status` | Today's spend vs budget for all campaigns |
| `analyze_performance` | AI insights via `ctx.ai` — trends, recommendations (optional: `campaign_id` for per-campaign scope) |

---

## Panel UI

Built on [Imperal Declarative UI](https://github.com/imperalcloud/imperal-sdk).

```
┌──── Left Panel (account_dashboard) ───────┐  ┌──── Right Panel (campaign_detail) ─────────┐
│  Web Host Most, LLC          ID: 187...   │  │  Summer Sale                    · ACTIVE    │
│  ─────────────────────────────────────    │  │  ID: 524140349  ·  Search                   │
│  $142.30    1,204    2.8%     $0.12       │  │  ─────────────────────────────────────────  │
│  Spend      Clicks   CTR      CPC         │  │  $50/day  ·  Max Clicks  ·  Active           │
│  ███████░░░░  71% of $200 budget          │  │  ─────────────────────────────────────────  │
│  ─────────────────────────────────────    │  │  [ Today ] [ Ad Groups (3) ]                │
│  CAMPAIGNS · 3 active  1 paused           │  │                                             │
│    Summer Sale      ACTIVE   [$50/day]    │  │  Today tab:                                 │
│    Brand Campaign   ACTIVE   [$30/day]    │  │    Spend vs Budget chart                    │
│    Retargeting      PAUSED   [$100/day]   │  │    Spend · Clicks · CTR · CPC               │
│    Shopping DE      ACTIVE   [$100/day]   │  │                                             │
│                               [+Campaign] │  │  Ad Groups tab:                             │
└───────────────────────────────────────────┘  │    Generic Search  · cpc: $1.00             │
                                               │    Brand Terms     · cpc: $2.50             │
                                               └─────────────────────────────────────────────┘
```

**Left panel states:** not_connected → OAuth → needs_setup (account picker) → dashboard
**Right panel states:** empty (no campaign selected) → loading → campaign detail

---

## Architecture

```
User (panel)
    ↓ ui.Open(oauth_url) — panel-driven, no chat required
Microsoft Azure (app c885090c, /common/ tenant)
    ↓ callback → Auth Gateway /v1/oauth/microsoft-ads/callback
    ↓ tokens stored in ext_store["msads_accounts"]
Panel auto-setup: list_customers_for_token → activate account
    ↓ Extension HTTP → whm-microsoft-ads-control (api-server:8090)
    X-Ms-Access-Token + X-Ms-Customer-Id + X-Ms-Account-Id headers
    ↓ microservice middleware → UserMicrosoftAdsClient → BingAds SOAP API v13
```

**OAuth flow (panel-driven, no chat):**
1. Panel renders Connect button with OAuth URL
2. User authorises on Microsoft → Auth Gateway saves tokens with `_needs_setup=True`
3. Panel auto-detects `_needs_setup=True` → discovers accounts → activates
4. If 1 account → auto-activate. Multiple accounts → shows picker list.

---

## File Structure

```
imperal-m-ads-extension/
├── CLAUDE.md                        # Full context for all collaborators + Claude
├── docs/
│   ├── extension.md                 # Full technical documentation
│   └── frontend.md                  # Frontend status (designer maintains)
├── main.py                          # Entry point — sys.modules isolation + imports
├── app.py                           # Extension setup, ChatExtension, helpers
├── handlers.py                      # connect, status, setup_account, switch_account, disconnect
├── handlers_campaigns.py            # list/get/create/update/pause/resume/delete campaigns
├── handlers_ads.py                  # list/create/update ad groups + RSA ads
├── handlers_keywords.py             # list/add/pause/resume/delete keywords, research, bid estimates
├── handlers_negative_keywords.py    # list/add/remove negative keywords
├── handlers_reports.py              # performance, search terms, budget status, AI analysis
├── skeleton.py                      # @ext.skeleton("msads") + skeleton_alert_msads; _get_dashboard_data() shared helper
├── panels.py                        # Left panel: account dashboard (all states)
├── panels_campaign.py               # Right panel: campaign detail + ad groups tabs
├── panels_ui.py                     # Shared helpers: formatters, badges, OAuth URL builder
├── system_prompt.txt                # LLM system prompt
├── imperal.json                     # Extension manifest v1.2.0
└── msads_providers/
    ├── __init__.py
    ├── helpers.py                   # OAuth constants, account helpers, location ID mapping
    ├── token_refresh.py             # Access token refresh logic
    └── msads_client.py              # HTTP client → whm-microsoft-ads-control
                                     # All API methods + _get/_post/_patch/_delete helpers
```

---

## Skeleton

| Tool | TTL | Returns |
|------|-----|---------|
| `skeleton_refresh_msads` | 300s | Scalar summary for AI classifier: `connected`, `account_name`, `campaigns_active/paused`, `alerts_count`, `today_spend` |
| `skeleton_alert_msads` | — | `notify()` when any campaign budget ≥ 90% spent |

`skeleton_refresh` also writes full `MsadsDashboard` to `ctx.cache("dashboard")` for panels.
Panels use cache-aside: hit → instant render; miss → `_get_dashboard_data()` live fetch.

**Note:** Campaign list in skeleton/cache contains metadata only (name, status, budget).
Per-campaign today spend/clicks require a separate `get_budget_status` call.

---

## Configuration

| Variable | Description |
|----------|-------------|
| `MS_ADS_CLIENT_ID` | Azure App client ID (`c885090c-cd0b-4074-8a12-58d05206ca36`) |
| `MS_ADS_CLIENT_SECRET` | Azure App client secret |
| `MS_ADS_REDIRECT_URI` | OAuth callback (`https://auth.imperal.io/v1/oauth/microsoft-ads/callback`) |
| `MSADS_API_URL` | Microservice URL (`https://api.webhostmost.com/microsoft-ads`) |
| `MSADS_JWT` | Service JWT for microservice authentication |

---

## Built with

- [imperal-sdk](https://github.com/imperalcloud/imperal-sdk) 3.5.x
- [Imperal Cloud](https://panel.imperal.io)
- Microsoft Advertising API v13 via [BingAds Python SDK](https://github.com/BingAds/BingAds-Python-SDK)
