"""Microsoft Ads · Right panel: campaign detail with chart and ad groups."""
from __future__ import annotations

import asyncio

from imperal_sdk import ui

from app import ext, _get_ready_account
import msads_providers.msads_client as api
from panels_ui import (
    campaign_badge, fmt_currency, fmt_pct, fmt_number,
)

SECTION = "msads_account"


@ext.panel("campaign_detail", slot="right", title="Campaign")
async def panel_campaign_detail(
    ctx,
    campaign_id: str = "",
    **kwargs,
) -> ui.UINode:
    """Campaign detail: spend-vs-budget chart + ad groups. Data from skeleton + one API call."""
    if not campaign_id:
        return ui.Stack([
            ui.Empty(
                message="Select a campaign from the left panel.",
                icon="MousePointer",
            ),
        ])

    acc, err = await _get_ready_account(ctx)
    if err:
        return ui.Stack([ui.Alert(type="error", message=err.message)])

    # ── Parallel fetch: campaign details + skeleton ───────────────────── #
    try:
        camp_data, skel = await asyncio.gather(
            api.get_campaign(ctx, acc, int(campaign_id)),
            ctx.skeleton.get(SECTION),
        )
    except Exception as exc:
        return ui.Stack([
            ui.Error(
                message=str(exc)[:200],
                retry=ui.Call("__panel__campaign_detail", campaign_id=campaign_id),
            ),
        ])

    skel      = skel or {}
    campaign  = camp_data.get("campaign", camp_data)
    ad_groups = camp_data.get("ad_groups", [])
    currency  = skel.get("currency", acc.get("currency", "$"))

    status    = campaign.get("status", "")
    is_active = status == "Active"
    budget    = float(campaign.get("daily_budget", campaign.get("budget_amount", 0)) or 0)
    camp_name = campaign.get("name", campaign_id)
    camp_type = campaign.get("campaign_type", "")
    bid_str   = campaign.get("bidding_scheme", "")

    # Find this campaign's today data in skeleton
    all_camps = skel.get("campaigns", [])
    camp_skel = next(
        (c for c in all_camps
         if str(c.get("id", c.get("campaign_id", ""))) == str(campaign_id)),
        {},
    )
    today_spend  = float(camp_skel.get("today_spend", camp_skel.get("spend", 0)) or 0)
    today_clicks = int(  camp_skel.get("clicks", 0) or 0)
    today_ctr    = float(camp_skel.get("ctr", 0) or 0)
    today_cpc    = float(camp_skel.get("avg_cpc", 0) or 0)

    # ── Header ────────────────────────────────────────────────────────── #
    header = ui.Stack([
        ui.Stack([
            ui.Text(content=camp_name, variant="heading"),
            campaign_badge(status),
        ], direction="h", gap=2),
        ui.Text(
            content=f"ID: {campaign_id}  ·  {camp_type}" if camp_type else f"ID: {campaign_id}",
            variant="caption",
        ),
    ])

    # ── Key campaign settings ─────────────────────────────────────────── #
    settings_stats = ui.Stats(columns=3, children=[
        ui.Stat(label="Daily Budget", value=fmt_currency(budget, currency),
                icon="DollarSign"),
        ui.Stat(label="Bidding",      value=_short_bid(bid_str),
                icon="TrendingUp"),
        ui.Stat(label="Status",       value=status,
                icon="Radio", color="green" if is_active else "gray"),
    ])

    # ── Tabs ──────────────────────────────────────────────────────────── #
    perf_tab = _build_perf_tab(
        budget, today_spend, today_clicks, today_ctr, today_cpc,
        currency, campaign_id, camp_name,
    )
    ag_tab = _build_ag_tab(ad_groups, currency, campaign_id, camp_name)

    tabs = ui.Tabs(tabs=[
        {"label": "Today",                         "content": [perf_tab]},
        {"label": f"Ad Groups ({len(ad_groups)})", "content": [ag_tab]},
    ], default_tab=0)

    # ── Sticky footer ─────────────────────────────────────────────────── #
    footer = ui.Stack([
        ui.Button(
            "Pause" if is_active else "Resume",
            icon="Pause" if is_active else "Play",
            variant="ghost",
            on_click=ui.Call(
                "pause_campaign" if is_active else "resume_campaign",
                campaign_id=campaign_id,
            ),
        ),
        ui.Button("7-day report", icon="BarChart2", variant="ghost",
                  on_click=ui.Send(f"Show 7-day performance for campaign '{camp_name}'")),
        ui.Button("AI Analyse", icon="Sparkles", variant="ghost",
                  on_click=ui.Send(f"Analyse performance of campaign '{camp_name}'")),
    ], direction="h", gap=2, sticky=True)

    return ui.Stack([header, ui.Divider(), settings_stats, ui.Divider(), tabs, footer])


# ─── Today's performance tab ──────────────────────────────────────────── #

def _build_perf_tab(
    budget: float, spend: float, clicks: int, ctr: float, cpc: float,
    currency: str, campaign_id: str, camp_name: str,
) -> ui.UINode:
    # Spend-vs-budget bar chart (skeleton data, instant)
    chart_data = [
        {"metric": "Spent Today", "amount": round(spend, 2)},
        {"metric": "Daily Budget", "amount": round(budget, 2)},
    ]

    pct = round(spend / budget * 100, 1) if budget else 0
    pct_color = "red" if pct >= 90 else "orange" if pct >= 70 else "green"
    pct_text  = f"{pct:.0f}% of budget used"

    alert_node: list = []
    if pct >= 90:
        alert_node = [ui.Alert(type="error",   message=f"Budget critical — {pct_text}")]
    elif pct >= 70:
        alert_node = [ui.Alert(type="warn",    message=f"Budget warning — {pct_text}")]

    today_kpis = ui.Stats(columns=2, children=[
        ui.Stat(label="Spend Today", value=fmt_currency(spend, currency),
                icon="DollarSign", color="blue"),
        ui.Stat(label="Clicks",      value=fmt_number(clicks),
                icon="MousePointer", color="green"),
        ui.Stat(label="CTR",         value=fmt_pct(ctr),
                icon="Percent"),
        ui.Stat(label="Avg CPC",     value=fmt_currency(cpc, currency),
                icon="Tag"),
    ])

    return ui.Stack([
        *alert_node,
        ui.Text(content="Spend vs Daily Budget", variant="label"),
        ui.Chart(data=chart_data, type="bar", x_key="metric", height=130),
        ui.Text(content=pct_text, variant="caption"),
        ui.Divider(label="TODAY'S METRICS"),
        today_kpis,
    ])


# ─── Ad Groups tab ────────────────────────────────────────────────────── #

def _build_ag_tab(
    ad_groups: list, currency: str, campaign_id: str, camp_name: str,
) -> ui.UINode:
    if not ad_groups:
        return ui.Stack([
            ui.Empty(
                message="No ad groups yet.",
                icon="Layers",
                action=ui.Send(f"Create an ad group in campaign '{camp_name}'"),
            ),
        ])

    items = []
    for ag in ad_groups:
        agid    = str(ag.get("id", ag.get("ad_group_id", "")))
        ag_name = ag.get("name", "")
        cpc     = float(ag.get("cpc_bid", 0) or 0)
        ag_st   = ag.get("status", "")

        items.append(ui.ListItem(
            id=agid,
            title=ag_name,
            subtitle=f"CPC: {fmt_currency(cpc, currency)}  ·  {ag_st}",
            icon="Layers",
            badge=campaign_badge(ag_st) if ag_st else None,
            actions=[
                {
                    "icon":     "List",
                    "label":    "Keywords",
                    "on_click": ui.Send(f"Show keywords in ad group '{ag_name}'"),
                },
                {
                    "icon":     "FileText",
                    "label":    "Ads",
                    "on_click": ui.Send(f"Show ads in ad group '{ag_name}'"),
                },
            ],
        ))

    return ui.Stack([
        ui.List(items=items, searchable=True),
        ui.Button("+ Ad Group", icon="Plus", variant="ghost",
                  on_click=ui.Send(f"Create an ad group in campaign '{camp_name}'")),
    ])


# ─── Bidding strategy labels ──────────────────────────────────────────── #

def _short_bid(scheme: str) -> str:
    _map = {
        "MaxClicks":          "Max Clicks",
        "MaxConversions":     "Max Conv.",
        "MaxConversionValue": "Max Value",
        "TargetCpa":          "Target CPA",
        "TargetRoas":         "Target ROAS",
        "ManualCpc":          "Manual CPC",
        "EnhancedCpc":        "eCPC",
    }
    return _map.get(scheme, scheme[:14] if scheme else "—")
