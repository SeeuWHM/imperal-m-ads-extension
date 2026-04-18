"""Microsoft Ads · Left panel: account dashboard."""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
from msads_providers.helpers import _all_accounts
from panels_ui import (
    campaign_badge, fmt_currency, fmt_pct, fmt_number,
    not_connected_view, needs_setup_view, error_view,
)

SECTION = "msads_account"


@ext.panel("account_dashboard", slot="left", title="Microsoft Ads", icon="TrendingUp")
async def panel_account_dashboard(ctx, **kwargs) -> ui.UINode:
    """Account KPIs, budget bar, and campaigns list — served from skeleton cache."""
    data = await ctx.skeleton.get(SECTION) or {}

    # ── Connection states ─────────────────────────────────────────────── #
    if not data.get("connected"):
        accounts = await _all_accounts(ctx)
        if not accounts:
            return not_connected_view()
        if any(a.get("_needs_setup") for a in accounts):
            return needs_setup_view()
        return error_view("Connection error. Try reconnecting.")

    # ── Extract skeleton data ─────────────────────────────────────────── #
    today     = data.get("today", {})
    campaigns = data.get("campaigns", [])
    alerts    = data.get("alerts", [])
    currency  = data.get("currency", "$")
    n_active  = data.get("campaigns_active", 0)
    n_paused  = data.get("campaigns_paused", 0)

    spend  = float(today.get("spend", 0) or 0)
    clicks = int(  today.get("clicks", 0) or 0)
    ctr    = float(today.get("ctr", 0) or 0)
    cpc    = float(today.get("avg_cpc", 0) or 0)

    budget_total = sum(
        float(c.get("daily_budget", c.get("budget_amount", 0)) or 0)
        for c in campaigns
    )
    pct_spent = round(spend / budget_total * 100, 1) if budget_total else 0

    # ── Budget progress bar ───────────────────────────────────────────── #
    _budget_color = "red" if pct_spent >= 90 else "yellow" if pct_spent >= 70 else "green"
    budget_bar = ui.Progress(
        value=min(int(pct_spent), 100),
        label=f"{fmt_currency(spend, currency)} / {fmt_currency(budget_total, currency)} today · {pct_spent:.0f}%",
        color=_budget_color,
    )

    # ── Budget alerts (max 2) ─────────────────────────────────────────── #
    alert_nodes = [
        ui.Alert(
            type="error" if a.get("type") == "budget_critical" else "warn",
            message=f"{a.get('campaign_name', 'Campaign')}: {a.get('pct_used', 0):.0f}% budget used",
        )
        for a in alerts[:2]
    ]

    # ── Today's KPI stats ─────────────────────────────────────────────── #
    kpi_stats = ui.Stats(columns=2, children=[
        ui.Stat(label="Spend Today",  value=fmt_currency(spend, currency),
                icon="DollarSign",   color="blue"),
        ui.Stat(label="Clicks",       value=fmt_number(clicks),
                icon="MousePointer", color="green"),
        ui.Stat(label="CTR",          value=fmt_pct(ctr),
                icon="Percent"),
        ui.Stat(label="Avg CPC",      value=fmt_currency(cpc, currency),
                icon="Tag"),
    ])

    # ── Campaigns list ────────────────────────────────────────────────── #
    camp_items = []
    for c in campaigns:
        cid       = str(c.get("id", c.get("campaign_id", "")))
        c_spend   = float(c.get("today_spend", c.get("spend", 0)) or 0)
        c_clicks  = int(c.get("clicks", 0) or 0)
        c_status  = c.get("status", "")
        is_active = c_status == "Active"

        camp_items.append(ui.ListItem(
            id=cid,
            title=c.get("name", "Campaign"),
            subtitle=f"{fmt_currency(c_spend, currency)} · {fmt_number(c_clicks)} clicks",
            badge=campaign_badge(c_status),
            icon="Play" if is_active else "Pause",
            on_click=ui.Call("__panel__campaign_detail", campaign_id=cid),
            actions=[{
                "icon":     "Pause" if is_active else "Play",
                "label":    "Pause" if is_active else "Resume",
                "on_click": ui.Call(
                    "pause_campaign" if is_active else "resume_campaign",
                    campaign_id=cid,
                ),
            }],
        ))

    camp_divider = ui.Divider(
        label=f"CAMPAIGNS  ·  {n_active} active  {n_paused} paused"
              if (n_active or n_paused) else f"CAMPAIGNS ({len(campaigns)})"
    )

    camp_list = (
        ui.List(items=camp_items, searchable=True, page_size=10)
        if camp_items else
        ui.Empty(
            message="No campaigns yet.",
            icon="BarChart2",
            action=ui.Send("Create a new Microsoft Ads campaign"),
        )
    )

    # ── Sticky footer ─────────────────────────────────────────────────── #
    footer = ui.Stack([
        ui.Button("+ Campaign", variant="primary", icon="Plus",
                  on_click=ui.Send("Create a new Microsoft Ads campaign")),
        ui.Button("", icon="RefreshCw", variant="ghost", size="sm",
                  on_click=ui.Call("__panel__account_dashboard")),
    ], direction="h", gap=2, sticky=True)

    return ui.Stack([
        ui.Header(
            text=data.get("account_name", "Microsoft Ads"),
            subtitle=f"ID: {data.get('account_id', '')}",
        ),
        budget_bar,
        *alert_nodes,
        kpi_stats,
        camp_divider,
        camp_list,
        footer,
    ])
