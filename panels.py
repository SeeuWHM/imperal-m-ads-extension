"""Microsoft Ads · Left panel: account dashboard."""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
from msads_providers.helpers import _all_accounts, COLLECTION
from msads_providers.msads_client import list_customers_for_token
from panels_ui import (
    campaign_badge, fmt_currency, fmt_pct, fmt_number,
    not_connected_view, error_view,
)

SECTION = "msads_account"


@ext.panel("account_dashboard", slot="left", title="Microsoft Ads", icon="TrendingUp")
async def panel_account_dashboard(
    ctx,
    disconnect: str = "",
    activate_id: str = "",
    doc_id: str = "",
    **kwargs,
) -> ui.UINode:
    """Left panel: handles connect / setup / dashboard states."""

    # ── Disconnect action ─────────────────────────────────────────────── #
    if disconnect == "1":
        accounts = await _all_accounts(ctx)
        for a in accounts:
            if a.get("doc_id"):
                try:
                    await ctx.store.delete(COLLECTION, a["doc_id"])
                except Exception:
                    pass
        return not_connected_view(ctx)

    # ── Activate specific account ─────────────────────────────────────── #
    if activate_id and doc_id:
        accounts = await _all_accounts(ctx)
        pending = next((a for a in accounts if a.get("doc_id") == doc_id), None)
        if pending:
            try:
                customers = await list_customers_for_token(ctx, pending.get("access_token", ""))
            except Exception:
                customers = []
            target = next((c for c in customers if str(c["account_id"]) == activate_id), None)
            if target:
                try:
                    await ctx.store.update(COLLECTION, doc_id, {
                        **{k: v for k, v in pending.items() if k != "doc_id"},
                        "customer_id":  str(target["customer_id"]),
                        "account_id":   str(target["account_id"]),
                        "account_name": target["account_name"],
                        "currency":     target.get("currency", "USD"),
                        "_needs_setup": False,
                    })
                except Exception:
                    pass
                return ui.Stack([
                    ui.Alert(type="success",
                             message=f"Connected: {target['account_name']} (ID: {target['account_id']})"),
                    ui.Button("", icon="RefreshCw", variant="primary", size="sm",
                              on_click=ui.Call("__panel__account_dashboard")),
                ])

    # ── Connection state check ────────────────────────────────────────── #
    data = await ctx.skeleton.get(SECTION) or {}

    if not data.get("connected"):
        accounts = await _all_accounts(ctx)
        if not accounts:
            return not_connected_view(ctx)

        if any(a.get("_needs_setup") for a in accounts):
            pending = next((a for a in accounts if a.get("_needs_setup")), {})
            display_name = pending.get("display_name", "")
            pending_doc_id = pending.get("doc_id", "")

            try:
                customers = await list_customers_for_token(ctx, pending.get("access_token", ""))
            except Exception:
                customers = []

            if not customers:
                return ui.Stack([
                    ui.Header(
                        text=display_name or "Microsoft Ads",
                        subtitle="No ad accounts found",
                    ),
                    ui.Alert(type="warn",
                             message="No Microsoft Advertising accounts found for this Microsoft account."),
                    ui.Text(
                        "Make sure you sign in with a Microsoft account that has access to Microsoft Advertising.",
                        variant="caption",
                    ),
                    ui.Button(
                        "Try a different account",
                        variant="primary",
                        full_width=True,
                        icon="RefreshCw",
                        on_click=ui.Call("__panel__account_dashboard", disconnect="1"),
                    ),
                ])

            if len(customers) == 1:
                target = customers[0]
                try:
                    await ctx.store.update(COLLECTION, pending_doc_id, {
                        **{k: v for k, v in pending.items() if k != "doc_id"},
                        "customer_id":  str(target["customer_id"]),
                        "account_id":   str(target["account_id"]),
                        "account_name": target["account_name"],
                        "currency":     target.get("currency", "USD"),
                        "_needs_setup": False,
                    })
                except Exception:
                    pass
                return ui.Stack([
                    ui.Alert(type="success",
                             message=f"Connected: {target['account_name']} (ID: {target['account_id']})"),
                    ui.Button("", icon="RefreshCw", variant="primary", size="sm",
                              on_click=ui.Call("__panel__account_dashboard")),
                ])

            # Multiple accounts
            return ui.Stack([
                ui.Header(
                    text=display_name or "Select account",
                    subtitle=f"{len(customers)} accounts available",
                ),
                ui.List(items=[
                    ui.ListItem(
                        id=str(c["account_id"]),
                        title=c["account_name"],
                        subtitle=f"ID: {c['account_id']} · {c.get('currency', 'USD')}",
                        icon="TrendingUp",
                        on_click=ui.Call(
                            "__panel__account_dashboard",
                            activate_id=str(c["account_id"]),
                            doc_id=pending_doc_id,
                        ),
                    )
                    for c in customers
                ]),
                ui.Divider(),
                ui.Button(
                    "Wrong account? Disconnect",
                    variant="ghost",
                    full_width=True,
                    on_click=ui.Call("__panel__account_dashboard", disconnect="1"),
                ),
            ])

        # Account is set up but skeleton not populated yet — show loading state
        ready = next((a for a in accounts if a.get("customer_id") and not a.get("_needs_setup")), None)
        if ready:
            return ui.Stack([
                ui.Header(
                    text=ready.get("account_name", "Microsoft Ads"),
                    subtitle=f"ID: {ready.get('account_id', '')}",
                ),
                ui.Alert(type="info", message="Loading your campaigns data…"),
                ui.Button("", icon="RefreshCw", variant="primary", size="sm",
                          on_click=ui.Call("__panel__account_dashboard")),
            ])
        return error_view("Connection error. Try reconnecting.", ctx)

    # ── Connected: extract skeleton data ──────────────────────────────── #
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

    _budget_color = "red" if pct_spent >= 90 else "yellow" if pct_spent >= 70 else "green"
    budget_bar = ui.Progress(
        value=min(int(pct_spent), 100),
        label=f"{fmt_currency(spend, currency)} / {fmt_currency(budget_total, currency)} today · {pct_spent:.0f}%",
        color=_budget_color,
    )

    alert_nodes = [
        ui.Alert(
            type="error" if a.get("type") == "budget_critical" else "warn",
            message=f"{a.get('campaign_name', 'Campaign')}: {a.get('pct_used', 0):.0f}% budget used",
        )
        for a in alerts[:2]
    ]

    kpi_stats = ui.Stats(columns=2, children=[
        ui.Stat(label="Spend Today",  value=fmt_currency(spend, currency),
                icon="DollarSign",   color="blue"),
        ui.Stat(label="Clicks",       value=fmt_number(clicks),
                icon="MousePointer", color="green"),
        ui.Stat(label="CTR",          value=fmt_pct(ctr),   icon="Percent"),
        ui.Stat(label="Avg CPC",      value=fmt_currency(cpc, currency), icon="Tag"),
    ])

    camp_items = []
    for c in campaigns:
        cid      = str(c.get("id", c.get("campaign_id", "")))
        c_spend  = float(c.get("today_spend", c.get("spend", 0)) or 0)
        c_clicks = int(c.get("clicks", 0) or 0)
        c_status = c.get("status", "")
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
        ui.Empty(message="No campaigns yet.", icon="BarChart2",
                 action=ui.Send("Create a new Microsoft Ads campaign"))
    )

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
