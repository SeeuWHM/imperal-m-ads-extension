"""Microsoft Ads · Right panel: campaign detail (ad groups, ads, keywords)."""
from __future__ import annotations

from imperal_sdk import ui

from app import ext, _get_ready_account
import msads_providers.msads_client as api


@ext.panel("campaign_detail", slot="right", title="Campaign")
async def panel_campaign_detail(
    ctx,
    campaign_id: str = "",
    section: str = "ad_groups",
    **kwargs,
):
    """Campaign detail: ad groups list or ads/keywords per ad group."""
    if not campaign_id:
        return ui.Stack([
            ui.Empty(message="Select a campaign from the left panel."),
        ])

    acc, err = await _get_ready_account(ctx)
    if err:
        return ui.Stack([ui.Alert(type="error", message=err.message)])

    # ── Campaign header ────────────────────────────────────────────────── #
    try:
        camp_data = await api.get_campaign(ctx, acc, int(campaign_id))
    except Exception as exc:
        return ui.Stack([ui.Alert(type="error", message=str(exc)[:150])])

    campaign  = camp_data.get("campaign", camp_data)
    ad_groups = camp_data.get("ad_groups", [])
    currency  = acc.get("currency", "$")
    status    = campaign.get("status", "")

    header = ui.Stack([
        ui.Header(
            title=campaign.get("name", campaign_id),
            subtitle=f"ID: {campaign_id}  ·  {campaign.get('campaign_type', '')}",
            badge=status.lower(),
        ),
        ui.Stack([
            ui.Stat(label="Budget",    value=f"{currency}{float(campaign.get('daily_budget', campaign.get('budget_amount', 0))):.2f}/day"),
            ui.Stat(label="Status",    value=status),
            ui.Stat(label="Bid",       value=campaign.get("bidding_scheme", "")),
        ], direction="horizontal", gap=3),
        ui.Stack([
            ui.Button(
                "Pause" if status == "Active" else "Resume",
                variant="ghost",
                on_click=ui.Call(
                    "pause_campaign" if status == "Active" else "resume_campaign",
                    campaign_id=campaign_id,
                ),
            ),
            ui.Button("+ Ad Group", variant="primary",
                      on_click=ui.Send(f"Create an ad group in campaign {campaign_id}")),
        ], direction="horizontal", gap=2),
        ui.Divider(),
    ])

    # ── Ad groups list ─────────────────────────────────────────────────── #
    if not ad_groups:
        ad_group_section = ui.Empty(
            message="No ad groups yet.",
            action=ui.Send(f"Create an ad group in campaign {campaign.get('name', campaign_id)}"),
        )
    else:
        ad_group_section = ui.List(
            items=[
                ui.ListItem(
                    id=str(ag.get("id", ag.get("ad_group_id", ""))),
                    title=ag.get("name", ""),
                    subtitle=(
                        f"Bid: {currency}{float(ag.get('cpc_bid', 0)):.2f}"
                        f"  ·  {ag.get('status', '')}"
                    ),
                    icon="Layers",
                    actions=[
                        {
                            "icon": "List",
                            "label": "Keywords",
                            "on_click": ui.Send(
                                f"Show keywords in ad group "
                                + str(ag.get("id", ag.get("ad_group_id", "")))
                            ),
                        },
                        {
                            "icon": "FileText",
                            "label": "Ads",
                            "on_click": ui.Send(
                                f"Show ads in ad group "
                                + str(ag.get("id", ag.get("ad_group_id", "")))
                            ),
                        },
                    ],
                )
                for ag in ad_groups
            ],
            searchable=True,
            page_size=20,
        )

    return ui.Stack([
        header,
        ui.Text("Ad Groups", weight="semibold"),
        ad_group_section,
    ])
