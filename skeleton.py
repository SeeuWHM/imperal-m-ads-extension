"""Microsoft Ads · Skeleton background tools.

skeleton_refresh: fetches today's metrics + campaign list (skeleton section: msads).
skeleton_alert:   sends proactive notification when a budget is critically low.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from app import ext, MsadsDashboard
import msads_providers.msads_client as api
from msads_providers.helpers import _active_account

log = logging.getLogger("microsoft-ads.skeleton")


async def _get_dashboard_data(ctx) -> MsadsDashboard:
    """Fetch live dashboard data. Called by skeleton_refresh and panel cache miss."""
    acc = await _active_account(ctx)
    if not acc or not acc.get("customer_id") or acc.get("_needs_setup"):
        return MsadsDashboard(connected=False)

    today = date.today().isoformat()
    try:
        perf_data = await api.get_report(
            ctx, acc, "summary",
            start_date=today, end_date=today,
            aggregation="Summary",
        )
        camps_data = await api.get_campaigns(ctx, acc)
    except Exception as exc:
        log.warning("_get_dashboard_data fetch failed: %s", exc)
        return MsadsDashboard(connected=True, error=str(exc)[:150])

    perf_rows = perf_data.get("rows", perf_data.get("data", []))
    camp_list = camps_data.get("campaigns", [])[:10]
    summary   = perf_rows[0] if perf_rows else {}

    alerts: list[dict[str, Any]] = []
    for c in camp_list:
        budget = float(c.get("daily_budget", c.get("budget_amount", 0)) or 0)
        spend  = float(c.get("today_spend",  c.get("spend",         0)) or 0)
        if budget > 0:
            pct = spend / budget * 100
            if pct >= 90:
                alerts.append({
                    "type":          "budget_critical",
                    "campaign_id":   str(c.get("id", c.get("campaign_id", ""))),
                    "campaign_name": c.get("name", ""),
                    "pct_used":      round(pct, 1),
                })
            elif pct >= 70:
                alerts.append({
                    "type":          "budget_warning",
                    "campaign_name": c.get("name", ""),
                    "pct_used":      round(pct, 1),
                })

    return MsadsDashboard(
        connected=True,
        account_name=acc.get("account_name", ""),
        account_id=acc.get("account_id", ""),
        currency=acc.get("currency", "USD"),
        today={
            "spend":       float(summary.get("Spend",       summary.get("spend",       0))),
            "clicks":      int(  summary.get("Clicks",      summary.get("clicks",      0))),
            "impressions": int(  summary.get("Impressions", summary.get("impressions", 0))),
            "ctr":         float(summary.get("Ctr",         summary.get("ctr",         0))),
            "avg_cpc":     float(summary.get("AverageCpc",  summary.get("avg_cpc",     0))),
            "conversions": float(summary.get("Conversions", summary.get("conversions", 0))),
        },
        campaigns=camp_list,
        campaigns_active=sum(1 for c in camp_list if c.get("status") == "Active"),
        campaigns_paused=sum(1 for c in camp_list if c.get("status") == "Paused"),
        alerts=alerts,
    )


@ext.skeleton("msads", ttl=300, alert=True)
async def skeleton_refresh(ctx) -> dict:
    dashboard = await _get_dashboard_data(ctx)
    if dashboard.connected:
        try:
            await ctx.cache.set("dashboard", dashboard, ttl_seconds=300)
        except Exception as exc:
            log.warning("dashboard cache write failed: %s", exc)
    return {"response": {
        "connected":        dashboard.connected,
        "account_name":     dashboard.account_name,
        "account_id":       dashboard.account_id,
        "currency":         dashboard.currency,
        "campaigns_active": dashboard.campaigns_active,
        "campaigns_paused": dashboard.campaigns_paused,
        "alerts_count":     len(dashboard.alerts),
        "today_spend":      dashboard.today.get("spend", 0) if dashboard.today else 0,
        "error":            dashboard.error or "",
    }}


@ext.tool(
    "skeleton_alert_msads",
    description="Proactive alert: notify user if any campaign budget is critically low.",
)
async def skeleton_alert(ctx, **kwargs) -> dict:
    # Read from cache written by skeleton_refresh — avoids redundant live API calls.
    cached = await ctx.cache.get("dashboard", model=MsadsDashboard)
    if not cached or not cached.connected:
        return {"response": {"alerts_sent": 0}}

    critical = [
        a.get("campaign_name", "")
        for a in cached.alerts
        if a.get("type") == "budget_critical"
    ]
    if not critical:
        return {"response": {"alerts_sent": 0}}

    names = ", ".join(critical)
    await ctx.notify(
        f"Budget alert: {len(critical)} campaign(s) nearly depleted — {names}",
        priority="high",
    )
    return {"response": {"alerts_sent": len(critical), "campaigns": names}}
