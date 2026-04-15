# imperal-m-ads-extension

[![Imperal SDK](https://img.shields.io/badge/imperal--sdk-1.5.0-blue)](https://pypi.org/project/imperal-sdk/)
[![Version](https://img.shields.io/badge/version-1.0.0-green)](https://github.com/SeeuWHM/imperal-m-ads-extension/releases)
[![License](https://img.shields.io/badge/license-LGPL--2.1-orange)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Imperal%20Cloud-purple)](https://panel.imperal.io)

**Microsoft Advertising AI manager extension for [Imperal Cloud](https://panel.imperal.io).**

Connect your Microsoft Ads account via OAuth and manage campaigns, ad groups, keywords, and performance reports through natural language.

---

## What It Does

Talk to it naturally:

```
"connect my Microsoft Ads account"
"show me all campaigns"
"pause the Summer Sale campaign"
"create a Search campaign with $50 daily budget"
"what keywords have the lowest quality score?"
"give me performance for last 7 days"
"research keywords for cloud hosting"
"why is my CTR dropping?"
```

Or manage campaigns from the panel — left sidebar shows account KPIs and campaign list, right panel shows campaign detail, ad groups, and performance reports.

---

## Capabilities

### Account Management
| Action | Description |
|--------|-------------|
| **connect** | OAuth2 authorization via Microsoft Azure (client_id `dd2bfaf0`) |
| **status** | Current account, today's KPIs, budget alerts |
| **setup_account** | Post-OAuth: discover and activate an ad account |
| **switch_account** | Switch between multiple connected accounts |
| **disconnect** | Remove account credentials |

### Campaigns
| Action | Description |
|--------|-------------|
| **list_campaigns** | All campaigns with budget, status, spend |
| **get_campaign** | Campaign detail + ad groups |
| **create_campaign** | Search / Shopping / Audience / DSA / PMax |
| **update_campaign** | Budget, status, bid strategy |
| **pause_campaign** | One-click pause |
| **resume_campaign** | One-click resume |

### Ad Groups & Ads
| Action | Description |
|--------|-------------|
| **list_ad_groups** | Ad groups by campaign |
| **create_ad_group** | With language and bid |
| **list_ads** | Ads by ad group |
| **create_ad** | RSA: ≥3 headlines, ≥2 descriptions |
| **update_ad** | Replace headlines / descriptions / URL |

### Keywords
| Action | Description |
|--------|-------------|
| **list_keywords** | By ad group — match type, quality score |
| **add_keywords** | Bulk: text + match_type + bid |
| **research_keywords** | AdInsight: ideas from seed keywords or URL |
| **get_bid_estimates** | MainLine1 / MainLine / FirstPage positions |

### Reports & AI Analysis
| Action | Description |
|--------|-------------|
| **get_performance** | Campaign / ad-group / keyword / summary, any date range |
| **get_search_terms** | Actual user search queries triggering your ads |
| **get_budget_status** | Today: spend vs budget, over/under-pacing |
| **analyze_performance** | AI insights via `ctx.ai` — trends, recommendations |

---

## Panel UI

Built on [Imperal Declarative UI](https://github.com/imperalcloud/imperal-sdk).

```
┌──── Left Panel (account_dashboard) ───────┐  ┌──── Right Panel ───────────────────────────┐
│  Microsoft Ads                            │  │  Campaign Detail / Reports                  │
│  ─────────────────────────────────────    │  │  ─────────────────────────────────────────  │
│  Spend      Clicks   CTR      CPC         │  │  [Campaign Detail tab]                      │
│  $142.30    1,204    2.8%     $0.12       │  │  Summer Sale · ACTIVE · $50/day             │
│  ███████░░░ 71% of $200 budget            │  │  Ad Groups (3)                              │
│  ─────────────────────────────────────    │  │    > Generic Search  · 15 keywords          │
│  Campaigns (4)                            │  │    > Brand Terms     · 8 keywords           │
│    Summer Sale      ACTIVE   $142/200     │  │    > Competitor      · 6 keywords           │
│    Brand Campaign   ACTIVE   $18/30       │  │                                             │
│    Retargeting      PAUSED   —            │  │  [Reports tab]                              │
│    Shopping DE      ACTIVE   $67/100      │  │  Performance · Budget · Keyword Research    │
└───────────────────────────────────────────┘  └─────────────────────────────────────────────┘
```

---

## File Structure

```
imperal-m-ads-extension/
├── main.py                  # Entry point — sys.modules cleanup + imports
├── app.py                   # Extension setup, ChatExtension, helpers, health check
├── handlers.py              # connect, status, setup_account, switch_account, disconnect
├── handlers_campaigns.py    # list/get/create/update/pause/resume campaigns
├── handlers_ads.py          # list/create/update ad groups + ads
├── handlers_keywords.py     # list/add keywords, research, bid estimates
├── handlers_reports.py      # performance, search terms, budget, AI analysis
├── skeleton.py              # skeleton_refresh_msads + skeleton_alert_msads
├── panels.py                # Left panel: account dashboard
├── panels_campaigns.py      # Right panel: campaign detail + ad groups
├── panels_reports.py        # Right panel: reports + keyword research
├── system_prompt.txt        # LLM system prompt
├── imperal.json             # Extension manifest
└── msads_providers/         # Internal package (renamed from providers/ to avoid import conflict)
    ├── __init__.py
    ├── helpers.py           # OAuth constants, account helpers
    ├── token_refresh.py     # Access token refresh logic
    └── msads_client.py      # HTTP client → whm-microsoft-ads-control microservice
```

---

## Architecture

```
User (chat)
    ↓ OAuth2 Authorization Code Flow
Microsoft Azure (app dd2bfaf0) → callback → Auth Gateway /v1/oauth/microsoft-ads/callback
    ↓ tokens stored in ctx.store["msads_accounts"]
Extension → HTTP → whm-microsoft-ads-control (:8090 on api-server)
    X-Ms-Access-Token + X-Ms-Customer-Id + X-Ms-Account-Id headers
    ↓ microservice middleware → per-request BingAds SOAP client → Microsoft Ads API v13
```

**OAuth flow:**
1. `connect()` → generates OAuth URL → user authorises on Microsoft
2. Auth Gateway callback → tokens saved in `msads_accounts` store collection
3. `setup_account()` → discovers available accounts → user selects one
4. All subsequent calls go through the microservice with `X-Ms-*` headers

---

## Skeleton

| Tool | TTL | Description |
|------|-----|-------------|
| `skeleton_refresh_msads` | 300s | Today's KPIs + campaign list + budget alerts |
| `skeleton_alert_msads` | — | `notify()` when budget ≥ 90% spent |

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MS_ADS_CLIENT_ID` | — | Azure App client ID |
| `MS_ADS_CLIENT_SECRET` | — | Azure App client secret |
| `MS_ADS_REDIRECT_URI` | `https://auth.imperal.io/v1/oauth/microsoft-ads/callback` | OAuth callback |
| `MSADS_API_URL` | `https://api.webhostmost.com/microsoft-ads` | Microservice URL |
| `MSADS_JWT` | — | Service JWT for microservice auth |

---

## Built with

- [imperal-sdk](https://github.com/imperalcloud/imperal-sdk) 1.5.0
- [Imperal Cloud](https://panel.imperal.io)
- Microsoft Advertising API v13 via [BingAds SDK](https://github.com/BingAds/BingAds-Python-SDK)
