# Changelog

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
