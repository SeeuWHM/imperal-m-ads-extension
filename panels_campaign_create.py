"""Microsoft Ads · Create campaign form."""
from __future__ import annotations

from imperal_sdk import ui


def _build_create_view() -> ui.UINode:
    form = ui.Form(
        children=[
            ui.Text(content="Campaign Name", variant="label"),
            ui.Input(placeholder="e.g. Summer Sale 2026", param_name="name"),
            ui.Text(content="Type", variant="label"),
            ui.Select(
                options=[
                    {"value": "Search",          "label": "Search"},
                    {"value": "Shopping",         "label": "Shopping"},
                    {"value": "Audience",         "label": "Audience"},
                    {"value": "DynamicSearchAds", "label": "Dynamic Search Ads"},
                    {"value": "PerformanceMax",   "label": "Performance Max"},
                ],
                param_name="campaign_type",
                placeholder="Select type...",
            ),
            ui.Text(content="Daily Budget", variant="label"),
            ui.Input(placeholder="50.00", param_name="daily_budget"),
            ui.Text(content="Bid Strategy", variant="label"),
            ui.Select(
                options=[
                    {"value": "MaxClicks",         "label": "Max Clicks"},
                    {"value": "MaxConversions",     "label": "Max Conversions"},
                    {"value": "MaxConversionValue", "label": "Max Conv. Value"},
                    {"value": "EnhancedCpc",        "label": "Enhanced CPC"},
                    {"value": "ManualCpc",          "label": "Manual CPC"},
                ],
                param_name="bid_strategy",
                placeholder="Select strategy...",
            ),
        ],
        action="create_campaign",
        submit_label="Create Campaign",
        defaults={"campaign_type": "Search", "bid_strategy": "MaxClicks"},
    )

    footer = ui.Stack([
        ui.Button("Cancel", variant="ghost",
                  on_click=ui.Call("__panel__campaign_detail", mode="", campaign_id="")),
    ], direction="h", sticky=True)

    return ui.Stack([
        ui.Header(text="New Campaign", level=3),
        ui.Divider(),
        form,
        footer,
    ])
