"""Microsoft Ads · Ad Group and Ad management handlers.

Functions: list_ad_groups, create_ad_group, list_ads, create_ad, update_ad.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app import chat, ActionResult, _get_ready_account
import msads_providers.msads_client as api

# ─── Models ──────────────────────────────────────────────────────────── #

class CampaignIdParams(BaseModel):
    """Identify a campaign."""
    campaign_id: str = Field(description="Campaign ID")


class CreateAdGroupParams(BaseModel):
    """Create a new ad group within a campaign."""
    campaign_id: str   = Field(description="Parent campaign ID")
    name:        str   = Field(description="Ad group name")
    cpc_bid:     float = Field(
        default=1.0,
        description="Default CPC bid in account currency (can be overridden per keyword)",
    )
    language:    str   = Field(
        default="English",
        description="Target language (e.g. English, Spanish, French)",
    )


class AdGroupIdParams(BaseModel):
    """Identify an ad group."""
    ad_group_id: str = Field(description="Ad group ID")


class CreateAdParams(BaseModel):
    """Create a Responsive Search Ad (RSA).

    Microsoft shows combinations of headlines + descriptions.
    At least 3 headlines and 2 descriptions are required.
    Max 30 chars per headline, max 90 chars per description.
    """
    ad_group_id:  str        = Field(description="Ad group ID")
    headlines:    list[str]  = Field(
        description="3–15 headlines (max 30 chars each). More = better AI rotation.",
    )
    descriptions: list[str]  = Field(
        description="2–4 descriptions (max 90 chars each).",
    )
    final_url:    str        = Field(description="Landing page URL (must start with https://)")
    path1:        str        = Field(default="", description="Display URL path 1 (max 15 chars, optional)")
    path2:        str        = Field(default="", description="Display URL path 2 (max 15 chars, optional)")


class UpdateAdParams(BaseModel):
    """Update an existing RSA ad."""
    ad_id:        str              = Field(description="Ad ID to update")
    ad_group_id:  str              = Field(description="Parent ad group ID (required by MS API)")
    headlines:    Optional[list[str]] = Field(default=None, description="New headlines (replaces all existing)")
    descriptions: Optional[list[str]] = Field(default=None, description="New descriptions (replaces all existing)")
    final_url:    Optional[str]       = Field(default=None, description="New landing page URL")


# ─── list_ad_groups ───────────────────────────────────────────────────── #

@chat.function(
    "list_ad_groups",
    action_type="read",
    description="List all ad groups within a campaign.",
)
async def fn_list_ad_groups(ctx, params: CampaignIdParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        data = await api.get_ad_groups(ctx, acc, int(params.campaign_id))
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)
    ad_groups = data.get("ad_groups", [])
    return ActionResult.success(
        data={"ad_groups": ad_groups, "total": len(ad_groups), "campaign_id": params.campaign_id},
        summary=f"{len(ad_groups)} ad group(s) in campaign {params.campaign_id}.",
    )


# ─── create_ad_group ──────────────────────────────────────────────────── #

@chat.function(
    "create_ad_group",
    action_type="write",
    event="ad_group.created",
    description="Create a new ad group within a campaign.",
)
async def fn_create_ad_group(ctx, params: CreateAdGroupParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        result = await api.create_ad_group(ctx, acc, {
            "campaign_id": int(params.campaign_id),
            "name":        params.name,
            "cpc_bid":     params.cpc_bid,
            "language":    params.language,
        })
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=False)
    # Microservice returns {"ad_group": {...}, "message": "..."}
    ad_group_id = (
        result.get("ad_group", {}).get("id")
        or result.get("ad_group_id")
        or result.get("id")
    )
    return ActionResult.success(
        data={
            "ad_group_id":  str(ad_group_id),
            "campaign_id":  params.campaign_id,
            "name":         params.name,
            "cpc_bid":      params.cpc_bid,
        },
        summary=f"Ad group '{params.name}' created (ID: {ad_group_id}).",
    )


# ─── list_ads ─────────────────────────────────────────────────────────── #

@chat.function(
    "list_ads",
    action_type="read",
    description="List all ads within an ad group.",
)
async def fn_list_ads(ctx, params: AdGroupIdParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        data = await api.get_ads(ctx, acc, int(params.ad_group_id))
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)
    ads = data.get("ads", [])
    return ActionResult.success(
        data={"ads": ads, "total": len(ads), "ad_group_id": params.ad_group_id},
        summary=f"{len(ads)} ad(s) in ad group {params.ad_group_id}.",
    )


# ─── create_ad ────────────────────────────────────────────────────────── #

@chat.function(
    "create_ad",
    action_type="write",
    event="ad.created",
    description=(
        "Create a Responsive Search Ad (RSA). "
        "Requires at least 3 headlines (≤30 chars each) and 2 descriptions (≤90 chars each). "
        "More headlines = better performance (Microsoft tests combinations automatically)."
    ),
)
async def fn_create_ad(ctx, params: CreateAdParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    if len(params.headlines) < 3:
        return ActionResult.error("At least 3 headlines are required.", retryable=False)
    if len(params.descriptions) < 2:
        return ActionResult.error("At least 2 descriptions are required.", retryable=False)

    body = {
        "ad_group_id":  int(params.ad_group_id),
        "headlines":    params.headlines,
        "descriptions": params.descriptions,
        "final_url":    params.final_url,
    }
    if params.path1:
        body["path1"] = params.path1
    if params.path2:
        body["path2"] = params.path2

    try:
        result = await api.create_ad(ctx, acc, body)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=False)

    # Microservice returns {"ad": {...}, "message": "..."}
    ad_id = (
        result.get("ad", {}).get("id")
        or result.get("ad_id")
        or result.get("id")
    )
    return ActionResult.success(
        data={
            "ad_id":        str(ad_id),
            "ad_group_id":  params.ad_group_id,
            "headlines":    params.headlines,
            "descriptions": params.descriptions,
            "final_url":    params.final_url,
        },
        summary=f"RSA ad created (ID: {ad_id}) in ad group {params.ad_group_id}.",
    )


# ─── update_ad ────────────────────────────────────────────────────────── #

@chat.function(
    "update_ad",
    action_type="write",
    event="ad.updated",
    description="Update an existing RSA ad. Provided fields replace the current values.",
)
async def fn_update_ad(ctx, params: UpdateAdParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    body: dict = {"ad_group_id": int(params.ad_group_id)}
    if params.headlines    is not None:
        body["headlines"]    = params.headlines
    if params.descriptions is not None:
        body["descriptions"] = params.descriptions
    if params.final_url    is not None:
        body["final_url"]    = params.final_url

    if len(body) == 1:  # only ad_group_id
        return ActionResult.error("No fields to update provided.", retryable=False)

    try:
        await api.update_ad(ctx, acc, int(params.ad_id), body)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    return ActionResult.success(
        data={"ad_id": params.ad_id, "ad_group_id": params.ad_group_id,
              "updated_fields": [k for k in body if k != "ad_group_id"]},
        summary=f"Ad {params.ad_id} updated.",
    )
