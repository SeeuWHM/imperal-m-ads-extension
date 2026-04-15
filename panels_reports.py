"""Microsoft Ads · Right panel: performance reports and keyword research."""
from __future__ import annotations

from imperal_sdk import ui

from app import ext, _get_ready_account
import msads_providers.msads_client as api


@ext.panel("reports", slot="right", title="Reports & Research")
async def panel_reports(
    ctx,
    report_type: str = "performance",
    date_from: str = "",
    date_to: str = "",
    **kwargs,
):
    """Performance overview + keyword research tool."""
    acc, err = await _get_ready_account(ctx)
    if err:
        return ui.Stack([ui.Alert(type="error", message=err.message)])

    # ── Tabs: Performance | Budget | Keywords ──────────────────────────── #
    tabs = ui.Accordion(items=[
        {
            "id":    "performance",
            "title": "Performance",
            "content": _performance_section(date_from, date_to),
        },
        {
            "id":    "budget",
            "title": "Budget Status",
            "content": ui.Stack([
                ui.Button("Load budget status", variant="ghost",
                          on_click=ui.Call("get_budget_status")),
            ]),
        },
        {
            "id":    "research",
            "title": "Keyword Research",
            "content": _research_section(),
        },
    ])

    return ui.Stack([
        ui.Header(title="Reports & Research", subtitle="Microsoft Advertising"),
        tabs,
    ])


# ─── Performance section ──────────────────────────────────────────────── #

def _performance_section(date_from: str, date_to: str) -> ui.Stack:
    """Date picker + quick-load buttons for performance reports."""
    return ui.Stack([
        ui.Text("Date range", weight="medium"),
        ui.Stack([
            ui.Input(
                placeholder="From: YYYY-MM-DD",
                on_submit=ui.Call("get_performance", level="campaign",
                                  date_from="__value__"),
            ),
            ui.Input(
                placeholder="To: YYYY-MM-DD",
                on_submit=ui.Call("get_performance", level="campaign",
                                  date_to="__value__"),
            ),
        ], direction="horizontal", gap=2),
        ui.Stack([
            ui.Button("Last 7 days",  variant="ghost",
                      on_click=ui.Send("Show campaign performance last 7 days")),
            ui.Button("Last 30 days", variant="ghost",
                      on_click=ui.Send("Show campaign performance last 30 days")),
            ui.Button("This month",   variant="ghost",
                      on_click=ui.Send("Show campaign performance this month")),
        ], direction="horizontal", gap=2),
        ui.Divider(label="Report type"),
        ui.Stack([
            ui.Button("Campaigns",    variant="ghost",
                      on_click=ui.Send("Show campaign performance")),
            ui.Button("Keywords",     variant="ghost",
                      on_click=ui.Send("Show keyword performance")),
            ui.Button("Search Terms", variant="ghost",
                      on_click=ui.Send("Show search terms report")),
        ], direction="horizontal", gap=2),
        ui.Divider(label="AI Analysis"),
        ui.Button("Analyse performance & get recommendations", variant="primary",
                  on_click=ui.Send("Analyse my Microsoft Ads performance")),
    ])


# ─── Keyword research section ─────────────────────────────────────────── #

def _research_section() -> ui.Stack:
    """Seed keyword input + language selector for AdInsight research."""
    return ui.Stack([
        ui.Text("Keyword Research via Microsoft AdInsight", weight="medium"),
        ui.Input(
            placeholder="Enter seed keywords (comma-separated) or a website URL…",
            on_submit=ui.Send("Research keywords for: __value__"),
        ),
        ui.Stack([
            ui.Button("Search",         variant="primary",
                      on_click=ui.Send("Research keywords")),
            ui.Button("Bid estimates",  variant="ghost",
                      on_click=ui.Send("Get bid estimates for my keywords")),
        ], direction="horizontal", gap=2),
        ui.Alert(
            type="info",
            message="Results will appear in the chat. Add keywords directly from there.",
        ),
    ])
