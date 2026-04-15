"""Microsoft Ads · Campaign management handlers.

Functions: list_campaigns, get_campaign, create_campaign,
           update_campaign, pause_campaign, resume_campaign.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app import chat, ActionResult, _get_ready_account
import msads_providers.msads_client as api

# ─── Models ──────────────────────────────────────────────────────────── #

class ListCampaignsParams(BaseModel):
    """Filter campaigns by status."""
    status: Literal["Active", "Paused", ""] = Field(
        default="",
        description="Filter by status: Active, Paused, or empty for all",
    )


class CampaignIdParams(BaseModel):
    """Identify a single campaign."""
    campaign_id: str = Field(description="Campaign ID (numeric string)")


class CreateCampaignParams(BaseModel):
    """Create a new Microsoft Ads campaign."""
    name:          str   = Field(description="Campaign name (unique within account)")
    campaign_type: Literal["Search", "Shopping", "Audience", "DynamicSearchAds", "PerformanceMax"] = Field(
        default="Search",
        description="Campaign type: Search (text ads), Shopping, Audience (display), DynamicSearchAds, PerformanceMax",
    )
    daily_budget:  float = Field(description="Daily budget in account currency (must be > 0)")
    bid_strategy:  Literal["EnhancedCpc", "ManualCpc", "MaxClicks", "MaxConversions", "MaxConversionValue"] = Field(
        default="MaxClicks",
        description="Bidding strategy",
    )
    target_cpa:    Optional[float] = Field(
        default=None,
        description="Target CPA (use with MaxConversions bidding, optional)",
    )
    target_roas:   Optional[float] = Field(
        default=None,
        description="Target ROAS (use with MaxConversionValue bidding, optional)",
    )


class UpdateCampaignParams(BaseModel):
    """Update campaign — only provided fields are changed."""
    campaign_id:  str            = Field(description="Campaign ID to update")
    daily_budget: Optional[float]= Field(default=None, description="New daily budget")
    status:       Optional[Literal["Active", "Paused"]] = Field(
        default=None, description="New status"
    )
    bid_strategy: Optional[Literal["EnhancedCpc", "ManualCpc", "MaxClicks", "MaxConversions", "MaxConversionValue"]] = Field(
        default=None, description="New bidding strategy"
    )
    target_cpa:   Optional[float]= Field(default=None, description="New target CPA")
    target_roas:  Optional[float]= Field(default=None, description="New target ROAS")


# ─── list_campaigns ───────────────────────────────────────────────────── #

@chat.function(
    "list_campaigns",
    action_type="read",
    description="List all campaigns with status, budget, and today's spend.",
)
async def fn_list_campaigns(ctx, params: ListCampaignsParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        data = await api.get_campaigns(ctx, acc, status=params.status)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)
    campaigns = data.get("campaigns", [])
    return ActionResult.success(
        data={"campaigns": campaigns, "total": len(campaigns), "filter": params.status or "all"},
        summary=f"{len(campaigns)} campaign(s) found.",
    )


# ─── get_campaign ─────────────────────────────────────────────────────── #

@chat.function(
    "get_campaign",
    action_type="read",
    description="Get full details for a single campaign including ad groups and performance.",
)
async def fn_get_campaign(ctx, params: CampaignIdParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        campaign = await api.get_campaign(ctx, acc, int(params.campaign_id))
        ad_groups = await api.get_ad_groups(ctx, acc, int(params.campaign_id))
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)
    return ActionResult.success(
        data={
            "campaign":  campaign,
            "ad_groups": ad_groups.get("ad_groups", []),
            "campaign_id": params.campaign_id,
        },
        summary=f"Campaign details loaded.",
    )


# ─── create_campaign ─────────────────────────────────────────────────────#

@chat.function(
    "create_campaign",
    action_type="write",
    event="campaign.created",
    description=(
        "Create a new Microsoft Ads campaign. "
        "Always ask the user for name, type, budget, and bidding strategy before calling."
    ),
)
async def fn_create_campaign(ctx, params: CreateCampaignParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    body: dict = {
        "name":          params.name,
        "campaign_type": params.campaign_type,
        "budget_amount": params.daily_budget,
        "bidding_scheme": params.bid_strategy,
    }
    if params.target_cpa:
        body["target_cpa"] = params.target_cpa
    if params.target_roas:
        body["target_roas"] = params.target_roas

    try:
        result = await api.create_campaign(ctx, acc, body)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=False)

    campaign_id = result.get("campaign_id") or result.get("id")
    return ActionResult.success(
        data={
            "campaign_id":   str(campaign_id),
            "campaign_name": params.name,
            "campaign_type": params.campaign_type,
            "daily_budget":  params.daily_budget,
            "bid_strategy":  params.bid_strategy,
        },
        summary=f"Campaign '{params.name}' created (ID: {campaign_id}).",
    )


# ─── update_campaign ──────────────────────────────────────────────────── #

@chat.function(
    "update_campaign",
    action_type="write",
    event="campaign.updated",
    description="Update campaign budget, status, or bidding strategy. Only provided fields change.",
)
async def fn_update_campaign(ctx, params: UpdateCampaignParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    body = {}
    if params.daily_budget is not None:
        body["budget_amount"]  = params.daily_budget
    if params.status is not None:
        body["status"]         = params.status
    if params.bid_strategy is not None:
        body["bidding_scheme"] = params.bid_strategy
    if params.target_cpa is not None:
        body["target_cpa"]     = params.target_cpa
    if params.target_roas is not None:
        body["target_roas"]    = params.target_roas

    if not body:
        return ActionResult.error("No fields to update provided.", retryable=False)

    try:
        await api.update_campaign(ctx, acc, int(params.campaign_id), body)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    return ActionResult.success(
        data={"campaign_id": params.campaign_id, "updated_fields": list(body.keys())},
        summary=f"Campaign {params.campaign_id} updated.",
    )


# ─── pause_campaign ───────────────────────────────────────────────────── #

@chat.function(
    "pause_campaign",
    action_type="write",
    event="campaign.paused",
    description="Pause an active campaign. Stops ad delivery immediately.",
)
async def fn_pause_campaign(ctx, params: CampaignIdParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        await api.update_campaign(ctx, acc, int(params.campaign_id), {"status": "Paused"})
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)
    return ActionResult.success(
        data={"campaign_id": params.campaign_id, "status": "Paused"},
        summary=f"Campaign {params.campaign_id} paused.",
    )


# ─── resume_campaign ──────────────────────────────────────────────────── #

@chat.function(
    "resume_campaign",
    action_type="write",
    event="campaign.resumed",
    description="Resume a paused campaign.",
)
async def fn_resume_campaign(ctx, params: CampaignIdParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        await api.update_campaign(ctx, acc, int(params.campaign_id), {"status": "Active"})
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)
    return ActionResult.success(
        data={"campaign_id": params.campaign_id, "status": "Active"},
        summary=f"Campaign {params.campaign_id} resumed.",
    )
