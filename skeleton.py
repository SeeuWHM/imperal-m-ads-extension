"""Microsoft Ads · Skeleton background tools.

skeleton_refresh_msads: refreshes today's metrics + campaign list.
skeleton_alert_msads:   sends proactive notification if budget is critical.
"""
from __future__ import annotations

import logging
from datetime import date

from app import ext
import msads_providers.msads_client as api
from msads_providers.helpers import _active_account

log = logging.getLogger("microsoft-ads.skeleton")

SECTION = "msads_account"  # skeleton section key


# ─── skeleton_refresh_msads ───────────────────────────────────────────── #

@ext.tool(
    "skeleton_refresh_msads",
    description="Background refresh: today's Microsoft Ads metrics, campaign list, budget alerts.",
)
async def skeleton_refresh(ctx, **kwargs) -> dict:
    acc = await _active_account(ctx)
    if not acc or not acc.get("customer_id") or acc.get("_needs_setup"):
        return {"response": {"connected": False}}

    today = date.today().isoformat()
    try:
        perf_data = await api.get_report(
            ctx, acc, "summary",
            start_date=today, end_date=today,
            aggregation="Summary",
        )
        camps_data = await api.get_campaigns(ctx, acc)
    except Exception as exc:
        log.warning("skeleton_refresh_msads fetch failed: %s", exc)
        return {"response": {"connected": True, "error": str(exc)[:150]}}

    perf_rows  = perf_data.get("rows", perf_data.get("data", []))
    camp_list  = camps_data.get("campaigns", [])[:10]  # top 10 for panel
    summary    = perf_rows[0] if perf_rows else {}

    # Budget alert logic
    alerts = []
    for c in camp_list:
        budget = float(c.get("daily_budget", c.get("budget_amount", 0)))
        spend  = float(c.get("today_spend", c.get("spend", 0)))
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

    return {"response": {
        "connected":         True,
        "account_name":      acc.get("account_name", ""),
        "account_id":        acc.get("account_id", ""),
        "currency":          acc.get("currency", "USD"),
        "today": {
            "spend":       float(summary.get("Spend",          summary.get("spend",       0))),
            "clicks":      int(  summary.get("Clicks",         summary.get("clicks",      0))),
            "impressions": int(  summary.get("Impressions",    summary.get("impressions", 0))),
            "ctr":         float(summary.get("Ctr",            summary.get("ctr",         0))),
            "avg_cpc":     float(summary.get("AverageCpc",     summary.get("avg_cpc",     0))),
            "conversions": float(summary.get("Conversions",    summary.get("conversions", 0))),
        },
        "campaigns":          camp_list,
        "campaigns_active":   sum(1 for c in camp_list if c.get("status") == "Active"),
        "campaigns_paused":   sum(1 for c in camp_list if c.get("status") == "Paused"),
        "alerts":             alerts,
    }}


# ─── skeleton_alert_msads ─────────────────────────────────────────────── #

@ext.tool(
    "skeleton_alert_msads",
    description="Proactive alert: notify user if any campaign budget is critically low.",
)
async def skeleton_alert(ctx, **kwargs) -> dict:
    data = await ctx.skeleton.get(SECTION) or {}
    if not data.get("connected"):
        return {"response": {}}

    critical = [a for a in data.get("alerts", []) if a["type"] == "budget_critical"]
    if not critical:
        return {"response": {"alerts_sent": 0}}

    names = ", ".join(a["campaign_name"] for a in critical)
    await ctx.notify(
        f"Budget alert: {len(critical)} campaign(s) nearly depleted — {names}",
        priority="high",
    )
    return {"response": {"alerts_sent": len(critical), "campaigns": names}}
