"""Microsoft Ads · Campaign detail view: overview tab and ad groups tab."""
from __future__ import annotations

from imperal_sdk import ui

from panels_ui import campaign_badge, fmt_currency, fmt_pct, fmt_number


def _build_detail_view(
    camp_data: dict,
    ad_groups: list,
    skel: dict,
    acc: dict,
    campaign_id: str,
    report_data: dict,
    report_range: str,
    active_tab: int,
) -> ui.UINode:
    campaign  = camp_data.get("campaign", camp_data)
    currency  = skel.get("currency", acc.get("currency", "$"))

    status    = campaign.get("status", "")
    is_active = status == "Active"
    budget    = float(campaign.get("daily_budget", campaign.get("budget_amount", 0)) or 0)
    camp_name = campaign.get("name", campaign_id)
    camp_type = campaign.get("campaign_type", "")
    bid_str   = campaign.get("bidding_scheme", "")

    all_camps = skel.get("campaigns", [])
    camp_skel = next(
        (c for c in all_camps
         if str(c.get("id", c.get("campaign_id", ""))) == str(campaign_id)),
        {},
    )
    today_spend = float(camp_skel.get("today_spend", camp_skel.get("spend", 0)) or 0)

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

    # ── Settings stats ────────────────────────────────────────────────── #
    settings_stats = ui.Stats(columns=3, children=[
        ui.Stat(label="Daily Budget", value=fmt_currency(budget, currency), icon="DollarSign"),
        ui.Stat(label="Bidding",      value=_short_bid(bid_str),            icon="TrendingUp"),
        ui.Stat(label="Status",       value=status,                         icon="Radio",
                color="green" if is_active else "gray"),
    ])

    # ── Tab selector (manual, fill container, no wrap) ────────────────── #
    tab_bar = ui.Stack([
        ui.Button(
            "Overview",
            variant="primary" if active_tab == 0 else "ghost",
            full_width=True,
            on_click=ui.Call("__panel__campaign_detail",
                             campaign_id=campaign_id, active_tab=0,
                             report_range=report_range),
        ),
        ui.Button(
            f"Ad Groups ({len(ad_groups)})",
            variant="primary" if active_tab == 1 else "ghost",
            full_width=True,
            on_click=ui.Call("__panel__campaign_detail",
                             campaign_id=campaign_id, active_tab=1,
                             report_range=report_range),
        ),
    ], direction="h", gap=1, wrap=False)

    # ── Tab content ───────────────────────────────────────────────────── #
    if active_tab == 1:
        tab_content = _build_ag_tab(ad_groups, currency, campaign_id, camp_name)
    else:
        tab_content = _build_overview_tab(
            budget, today_spend, report_data, report_range, currency, campaign_id,
        )

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
        ui.Button("AI Analyse", icon="Sparkles", variant="ghost",
                  on_click=ui.Send(f"Analyse performance of campaign '{camp_name}'")),
    ], direction="h", gap=2, sticky=True)

    return ui.Stack([header, ui.Divider(), settings_stats, ui.Divider(),
                     tab_bar, tab_content, footer])


# ─── Period filter ────────────────────────────────────────────────────── #

def _period_filter(report_range: str, campaign_id: str) -> ui.UINode:
    _ranges = [("7D", "LAST_7_DAYS"), ("30D", "LAST_30_DAYS"), ("This month", "THIS_MONTH")]
    return ui.Stack([
        ui.Button(
            label,
            variant="primary" if report_range == val else "ghost",
            size="sm",
            on_click=ui.Call("__panel__campaign_detail",
                             campaign_id=campaign_id,
                             report_range=val,
                             active_tab=0),
        )
        for label, val in _ranges
    ], direction="h", gap=1)


# ─── Overview tab ─────────────────────────────────────────────────────── #

def _build_overview_tab(
    budget: float,
    today_spend: float,
    report_data: dict,
    report_range: str,
    currency: str,
    campaign_id: str,
) -> ui.UINode:
    pct      = round(today_spend / budget * 100, 1) if budget else 0
    pct_text = f"{pct:.0f}% of daily budget used"

    alert_node: list = []
    if pct >= 90:
        alert_node = [ui.Alert(type="error", message=f"Budget critical — {pct_text}")]
    elif pct >= 70:
        alert_node = [ui.Alert(type="warn",  message=f"Budget warning — {pct_text}")]

    budget_chart = [
        {"metric": "Spent Today",  "amount": round(today_spend, 2)},
        {"metric": "Daily Budget", "amount": round(budget, 2)},
    ]

    rows = report_data.get("rows", report_data.get("data", []))

    period_kpis_node: list = []
    chart_node: list = []

    if rows:
        total_spend  = sum(float(r.get("Spend",       r.get("spend",       0)) or 0) for r in rows)
        total_clicks = sum(int(  r.get("Clicks",      r.get("clicks",      0)) or 0) for r in rows)
        total_impr   = sum(int(  r.get("Impressions", r.get("impressions", 0)) or 0) for r in rows)
        avg_ctr = total_clicks / total_impr * 100 if total_impr else 0
        avg_cpc = total_spend  / total_clicks     if total_clicks else 0

        period_kpis_node = [
            ui.Divider(label="PERIOD METRICS"),
            ui.Stats(columns=2, children=[
                ui.Stat(label="Spend",   value=fmt_currency(total_spend, currency),  icon="DollarSign",   color="blue"),
                ui.Stat(label="Clicks",  value=fmt_number(total_clicks),             icon="MousePointer", color="green"),
                ui.Stat(label="CTR",     value=fmt_pct(avg_ctr),                     icon="Percent"),
                ui.Stat(label="Avg CPC", value=fmt_currency(avg_cpc, currency),      icon="Tag"),
            ]),
        ]

        chart_data = []
        for r in rows:
            day   = str(r.get("TimePeriod", r.get("Date", r.get("date", ""))))
            spend = float(r.get("Spend", r.get("spend", 0)) or 0)
            chart_data.append({"day": day[-5:] if len(day) >= 5 else day, "spend": round(spend, 2)})

        chart_node = [
            ui.Divider(label="DAILY SPEND"),
            ui.Chart(data=chart_data, type="bar", x_key="day", height=150),
        ]

    return ui.Stack([
        _period_filter(report_range, campaign_id),
        *alert_node,
        ui.Text(content="Spend vs Daily Budget", variant="label"),
        ui.Chart(data=budget_chart, type="bar", x_key="metric", height=130),
        ui.Text(content=pct_text, variant="caption"),
        *period_kpis_node,
        *chart_node,
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
        ui.List(items=items),
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
