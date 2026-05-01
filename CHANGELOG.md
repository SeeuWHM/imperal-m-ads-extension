# Changelog

## [1.2.0] — 2026-05-01

### Architecture

- **`MsadsDashboard` cache model** — Pydantic model registered via `@ext.cache_model("msads_dashboard")` in `app.py`. Panel-side runtime state (account KPIs, campaign list, alerts) now travels through `ctx.cache` with full type safety instead of ad-hoc dicts.
- **`_get_dashboard_data()` shared helper** — single fetch function called by both `skeleton_refresh` (every 300 s) and panels on cache miss. Eliminates duplicate fetch logic.
- **`skeleton_refresh` migrated to `@ext.skeleton` decorator** — canonical SDK v1.6.0 pattern. Returns `{"response": {scalar fields}}` per SDK contract, not `ActionResult`. AI classifier receives concise scalars: `connected`, `account_name`, `campaigns_active/paused`, `alerts_count`, `today_spend`. Full dashboard written to `ctx.cache` for panels.

### Fixed

- **`main.py` sub-module isolation** — `msads_providers` sub-modules (`helpers`, `msads_client`, `token_refresh`) were not cleaned from `sys.modules` on hot-reload, causing stale code to persist. Fixed with `k.startswith("msads_providers.")`. Removed stale `"providers"` entry.
- **`imperal.json` skeleton parameters** — `skeleton_refresh_msads` and `skeleton_alert_msads` had `kwargs: required: true` in their manifest parameter declarations. Skeleton tools take no kwargs; removed.
- **`msads_providers/helpers.py`** — `ctx.user.id` → `ctx.user.imperal_id` (breaking rename in SDK 3.0.0). OAuth state payload now encodes the correct user identifier.
- **`app.py`** — removed deprecated `model=` parameter from `ChatExtension` constructor (deprecated SDK 3.3.0, removed SDK 4.0.0).

### Changed

- **`handlers_reports.py` `analyze_performance`** — added `campaign_id: Optional[str]` parameter for per-campaign AI analysis (default: account-wide). `asyncio` import promoted to module level.
- **`main.py`** — version string updated to `v1.2.0`.

---

## [1.1.1] — 2026-04-25

### Fixed

- **`fn_status`** — removed `ctx.skeleton.get()` call which raises `SkeletonAccessForbidden` in SDK v1.6.0 inside `@chat.function` context. `today` stats now return `{}` gracefully; accounts list unaffected.
- **`skeleton_alert_msads`** — replaced `ctx.skeleton.get()` with `ctx.cache.get("dashboard")` (SDK v1.6.0: `ctx.skeleton` forbidden outside `@ext.skeleton` tools).
- **`panels.py`, `panels_campaign.py`** — removed `ctx.skeleton.get()` from `@ext.panel` handlers. Panel data path now uses `ctx.cache.get_or_fetch()` exclusively.

---

## [1.1.0] — 2026-04-22

### Fixed

- **`connect()`** — corrected `action_type` to `"read"` (connect is a read + UI action, not a write). Added `ActionResult.ui` button for the OAuth URL so the panel renders the Connect button inline in chat.
- **`SetupAccountParams`** — renamed `account_id` → `ms_account_id` to bypass scope guard that conflicted with the `account_id` field returned in the response data.
- **`fn_setup_account`** — `account_id` param now truly optional; function returns available accounts list when no ID given.
- **OAuth consumer tenant** — fixed tenant resolution in `_oauth_state`; multi-tenant `common` endpoint now correctly propagates `tenant_id` through the state JWT.
- **`ActionResult.error`** — fixed incorrect attribute access pattern in several handlers.
- **Panel actions** — replaced `ui.Send` with `ui.Call` for panel button actions (platform GAP-B: `ui.Send` from panel `ListItem.actions` is a no-op).

### Changed

- Skeleton updated to include `create_ag` mode note; panel routing docs clarified.

---

## [1.0.0] — 2026-04-15

### Added

- OAuth2 account connection via Microsoft Azure (Authorization Code Flow)
- 24 chat functions: account management (5), campaigns (6), ad groups + ads (5), keywords (4), reports (4)
- Domain health monitoring: campaign status, budget pacing, keyword quality scores
- AI performance analysis via `ctx.ai` — trends, CTR/CPC diagnostics, recommendations
- Keyword research via AdInsight — seed keywords or URL, bid estimates per position
- 3 panels: account dashboard (left), campaign detail (right), reports + research (right)
- Skeleton: today's KPIs + budget alerts (refresh every 5 min, alert at ≥90% budget)
- Multi-tenant support: X-Ms-* headers → per-request BingAds client in microservice
- Health check endpoint: verifies microservice connectivity + OAuth config
- `msads_providers/` package — internal OAuth helpers, token refresh, HTTP client
