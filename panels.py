"""Microsoft Ads · Left panel: account dashboard and campaigns list."""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
from msads_providers.helpers import _all_accounts, COLLECTION

SECTION = "msads_account"


@ext.panel("account_dashboard", slot="left", title="Microsoft Ads", icon="TrendingUp")
async def panel_account_dashboard(ctx, **kwargs):
    """Account KPIs, budget progress, and campaigns list from skeleton cache."""
    data = await ctx.skeleton.get(SECTION) or {}

    # ── Not connected ──────────────────────────────────────────────────── #
    if not data.get("connected"):
        accounts = await _all_accounts(ctx)
        if not accounts:
            return ui.Stack([
                ui.Empty(
                    message="No Microsoft Ads account connected.",
                    action=ui.Send("Connect Microsoft Ads"),
                ),
            ])
        if any(a.get("_needs_setup") for a in accounts):
            return ui.Stack([
                ui.Alert(type="warning",
                         message="Authorised! Select your ad account to continue."),
                ui.Button("Setup account", variant="primary",
                          on_click=ui.Send("Setup my Microsoft Ads account")),
            ])
        return ui.Stack([
            ui.Alert(type="error", message="Connection error. Check your account."),
            ui.Button("Reconnect", variant="primary",
                      on_click=ui.Send("Reconnect Microsoft Ads")),
        ])

    # ── Data ───────────────────────────────────────────────────────────── #
    today     = data.get("today", {})
    campaigns = data.get("campaigns", [])
    alerts    = data.get("alerts", [])
    currency  = data.get("currency", "$")

    budget_total = sum(float(c.get("daily_budget", c.get("budget_amount", 0)))
                       for c in campaigns)
    spend        = float(today.get("spend", 0))
    pct_spent    = round(spend / budget_total * 100, 1) if budget_total else 0
    bar_color    = "red" if pct_spent >= 90 else "orange" if pct_spent >= 70 else "green"

    # ── Build panel ────────────────────────────────────────────────────── #
    children = [
        # Header
        ui.Header(
            title=data.get("account_name", "Microsoft Ads"),
            subtitle=f"ID: {data.get('account_id', '')}",
        ),

        # Budget bar
        ui.Stack([
            ui.Text(
                f"Today: {currency}{spend:.2f} / {currency}{budget_total:.2f}",
                weight="medium",
            ),
            ui.Progress(value=int(pct_spent), color=bar_color),
        ], gap=1),

        # KPIs grid
        ui.Grid([
            ui.Stat(label="Clicks",      value=str(today.get("clicks", 0))),
            ui.Stat(label="Impressions", value=str(today.get("impressions", 0))),
            ui.Stat(label="CTR",         value=f"{float(today.get('ctr', 0)):.1f}%"),
            ui.Stat(label="Avg CPC",     value=f"{currency}{float(today.get('avg_cpc', 0)):.2f}"),
        ], columns=2),
    ]

    # Budget alerts
    for a in alerts:
        children.append(ui.Alert(
            type="error" if a["type"] == "budget_critical" else "warning",
            message=f"{a['campaign_name']}: {a['pct_used']:.0f}% budget used",
        ))

    children.append(ui.Divider())

    # Campaigns list
    children.append(ui.List(
        items=[
            ui.ListItem(
                id=str(c.get("id", c.get("campaign_id", ""))),
                title=c.get("name", ""),
                subtitle=(
                    f"{currency}{float(c.get('today_spend', c.get('spend', 0))):.2f}"
                    f" · {c.get('clicks', 0)} clicks"
                ),
                icon="Play" if c.get("status") == "Active" else "Pause",
                actions=[
                    {
                        "icon": "Pause" if c.get("status") == "Active" else "Play",
                        "on_click": ui.Call(
                            "pause_campaign" if c.get("status") == "Active" else "resume_campaign",
                            campaign_id=str(c.get("id", c.get("campaign_id", ""))),
                        ),
                    },
                ],
                on_click=ui.Call(
                    "get_campaign",
                    campaign_id=str(c.get("id", c.get("campaign_id", ""))),
                ),
            )
            for c in campaigns
        ],
        searchable=True,
        page_size=15,
    ))

    # Action bar
    children.append(ui.Stack([
        ui.Button("+ Campaign", variant="primary",
                  on_click=ui.Send("Create a new Microsoft Ads campaign")),
        ui.Button("Reports", variant="ghost",
                  on_click=ui.Call("get_budget_status")),
    ], direction="horizontal", gap=2, sticky=True))

    return ui.Stack(children)
