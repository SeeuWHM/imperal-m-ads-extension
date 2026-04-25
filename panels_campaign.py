"""Microsoft Ads · Right panel router: campaign detail and create form."""
from __future__ import annotations

import asyncio

from imperal_sdk import ui

from app import ext, _get_ready_account
import msads_providers.msads_client as api
from panels_campaign_create import _build_create_view
from panels_campaign_detail import _build_detail_view
from panels_ui import date_range

SECTION = "msads_account"


@ext.panel("campaign_detail", slot="right", title="Campaign")
async def panel_campaign_detail(
    ctx,
    campaign_id: str = "",
    mode: str = "",
    report_range: str = "LAST_7_DAYS",
    active_tab: int = 0,
    **kwargs,
) -> ui.UINode:
    if mode == "create":
        acc, err = await _get_ready_account(ctx)
        if err:
            return ui.Stack([ui.Alert(type="error", message=err.error or err.summary)])
        return _build_create_view()

    if not campaign_id:
        return ui.Stack([
            ui.Empty(
                message="Select a campaign from the left panel.",
                icon="MousePointer",
            ),
        ])

    acc, err = await _get_ready_account(ctx)
    if err:
        return ui.Stack([ui.Alert(type="error", message=err.error or err.summary)])

    start, end = date_range(report_range)

    # Required calls — panel can't render without these
    try:
        camp_data, ag_data = await asyncio.gather(
            api.get_campaign(ctx, acc, int(campaign_id)),
            api.get_ad_groups(ctx, acc, int(campaign_id)),
        )
    except Exception as exc:
        return ui.Stack([
            ui.Alert(type="error", message=str(exc)[:200]),
            ui.Button("Retry", icon="RefreshCw", variant="secondary",
                      on_click=ui.Call("__panel__campaign_detail", campaign_id=campaign_id)),
        ])

    # Optional: period performance report — may fail on Basic Developer Token (graceful degradation)
    report_data: dict = {}
    try:
        report_data = await api.get_report(
            ctx, acc, "campaign",
            start_date=start, end_date=end,
            aggregation="Daily",
            campaign_id=int(campaign_id),
        )
    except Exception:
        pass  # report_data stays {}; _build_overview_tab renders without period chart

    ad_groups = ag_data.get("ad_groups", [])

    return _build_detail_view(
        camp_data, ad_groups, {}, acc, campaign_id,
        report_data or {}, report_range, active_tab,
    )
