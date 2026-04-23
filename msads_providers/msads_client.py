"""Microsoft Ads · HTTP client for whm-microsoft-ads-control microservice.

All API calls go through this module. The microservice handles bingads SOAP
complexity; this module is a thin async HTTP layer on top.

Multi-tenant: X-Ms-Access-Token + X-Ms-Customer-Id + X-Ms-Account-Id headers
trigger the middleware in the microservice to use the user's account instead
of the WHM singleton. The microservice's developer_token is always WHM's.
"""
from __future__ import annotations

import logging
from typing import Any

from imperal_sdk import Context

from .helpers import MSADS_API_URL, MSADS_JWT
from .token_refresh import _refresh_token_if_needed

log = logging.getLogger("microsoft-ads.client")


# ─── Internal HTTP helpers ────────────────────────────────────────────── #

def _headers(acc: dict) -> dict:
    """Build request headers for a user account (multi-tenant path)."""
    return {
        "Authorization":    f"Bearer {MSADS_JWT}",
        "X-Ms-Access-Token": acc["access_token"],
        "X-Ms-Customer-Id":  str(acc["customer_id"]),
        "X-Ms-Account-Id":   str(acc["account_id"]),
    }


def _discovery_headers(access_token: str) -> dict:
    """Headers for account discovery — only access_token, no account IDs yet."""
    return {
        "Authorization":    f"Bearer {MSADS_JWT}",
        "X-Ms-Access-Token": access_token,
    }


async def _get(ctx: Context, acc: dict, path: str, **params) -> Any:
    acc = await _refresh_token_if_needed(ctx, acc)
    r = await ctx.http.get(
        f"{MSADS_API_URL}{path}",
        headers=_headers(acc),
        params={k: v for k, v in params.items() if v is not None},
    )
    r.raise_for_status()
    return r.json()


async def _post(ctx: Context, acc: dict, path: str, body: dict) -> Any:
    acc = await _refresh_token_if_needed(ctx, acc)
    r = await ctx.http.post(f"{MSADS_API_URL}{path}", headers=_headers(acc), json=body)
    r.raise_for_status()
    return r.json()


async def _patch(
    ctx: Context, acc: dict, path: str, body: dict, *, params: dict | None = None
) -> Any:
    acc = await _refresh_token_if_needed(ctx, acc)
    r = await ctx.http.patch(
        f"{MSADS_API_URL}{path}",
        headers=_headers(acc),
        json=body,
        params={k: v for k, v in (params or {}).items() if v is not None},
    )
    r.raise_for_status()
    return r.json()


async def _delete(
    ctx: Context, acc: dict, path: str, *, params: dict | None = None, body: dict | None = None
) -> Any:
    acc = await _refresh_token_if_needed(ctx, acc)
    kwargs: dict = {
        "headers": _headers(acc),
        "params": {k: v for k, v in (params or {}).items() if v is not None},
    }
    if body is not None:
        kwargs["json"] = body
    r = await ctx.http.delete(f"{MSADS_API_URL}{path}", **kwargs)
    r.raise_for_status()
    return r.json()


# ─── Account ─────────────────────────────────────────────────────────── #

async def list_customers_for_token(ctx: Context, access_token: str) -> list[dict]:
    """Discover all MS Ads accounts accessible with this access_token.
    Called by setup_account() before customer_id/account_id are known.
    """
    r = await ctx.http.get(
        f"{MSADS_API_URL}/v1/account/customers",
        headers=_discovery_headers(access_token),
    )
    if r.status_code == 200:
        return r.json().get("customers", [])
    log.warning("list_customers_for_token: %s %s", r.status_code, r.text()[:200])
    return []


async def get_account_info(ctx: Context, acc: dict) -> dict:
    return await _get(ctx, acc, "/v1/account")


# ─── Campaigns ───────────────────────────────────────────────────────── #

async def get_campaigns(ctx: Context, acc: dict, status: str = "") -> dict:
    return await _get(ctx, acc, "/v1/campaigns",
                      **{"status": status} if status else {})


async def get_campaign(ctx: Context, acc: dict, campaign_id: int) -> dict:
    return await _get(ctx, acc, f"/v1/campaigns/{campaign_id}")


async def create_campaign(ctx: Context, acc: dict, data: dict) -> dict:
    return await _post(ctx, acc, "/v1/campaigns", data)


async def update_campaign(ctx: Context, acc: dict, campaign_id: int, data: dict) -> dict:
    return await _patch(ctx, acc, f"/v1/campaigns/{campaign_id}", data)


# ─── Ad Groups ───────────────────────────────────────────────────────── #

async def get_ad_groups(ctx: Context, acc: dict, campaign_id: int) -> dict:
    return await _get(ctx, acc, "/v1/ad-groups", campaign_id=campaign_id)


async def create_ad_group(ctx: Context, acc: dict, data: dict) -> dict:
    return await _post(ctx, acc, "/v1/ad-groups", data)


# ─── Ads ─────────────────────────────────────────────────────────────── #

async def get_ads(ctx: Context, acc: dict, ad_group_id: int) -> dict:
    return await _get(ctx, acc, "/v1/ads", ad_group_id=ad_group_id)


async def create_ad(ctx: Context, acc: dict, data: dict) -> dict:
    return await _post(ctx, acc, "/v1/ads", data)


async def update_ad(ctx: Context, acc: dict, ad_id: int, ad_group_id: int, data: dict) -> dict:
    # ad_group_id is a required query param: PATCH /v1/ads/{ad_id}?ad_group_id=N
    return await _patch(ctx, acc, f"/v1/ads/{ad_id}", data, params={"ad_group_id": ad_group_id})


# ─── Keywords ────────────────────────────────────────────────────────── #

async def get_keywords(ctx: Context, acc: dict, ad_group_id: int) -> dict:
    return await _get(ctx, acc, "/v1/keywords", ad_group_id=ad_group_id)


async def add_keywords(ctx: Context, acc: dict, data: dict) -> dict:
    return await _post(ctx, acc, "/v1/keywords", data)


# ─── AdInsight ───────────────────────────────────────────────────────── #

async def keyword_ideas(ctx: Context, acc: dict, data: dict) -> dict:
    return await _post(ctx, acc, "/v1/insights/keyword-ideas", data)


async def bid_estimates(ctx: Context, acc: dict, data: dict) -> dict:
    return await _post(ctx, acc, "/v1/insights/bid-estimates", data)


# ─── Reports ─────────────────────────────────────────────────────────── #

async def get_report(
    ctx: Context,
    acc: dict,
    report_type: str,
    start_date: str,
    end_date: str,
    aggregation: str = "Daily",
    campaign_id: int | None = None,
    ad_group_id: int | None = None,
) -> dict:
    """Fetch a performance report. report_type maps to GET /v1/reports/{type}.

    campaign_id param handling:
      - /v1/reports/campaign  → expects `campaign_ids` (comma-separated string)
      - all other endpoints   → expect `campaign_id` (int)
    """
    params: dict = {
        "start_date":  start_date,
        "end_date":    end_date,
        "aggregation": aggregation,
    }
    if campaign_id is not None:
        if report_type == "campaign":
            params["campaign_ids"] = str(campaign_id)
        else:
            params["campaign_id"] = campaign_id
    if ad_group_id is not None:
        params["ad_group_id"] = ad_group_id

    return await _get(ctx, acc, f"/v1/reports/{report_type}", **params)


# ─── Keywords (extended) ──────────────────────────────────────────────────── #

async def update_keyword(
    ctx: Context, acc: dict, keyword_id: int, ad_group_id: int, data: dict
) -> dict:
    """Update a keyword's status or bid. ad_group_id required by MS API."""
    return await _patch(
        ctx, acc, f"/v1/keywords/{keyword_id}", data,
        params={"ad_group_id": ad_group_id},
    )


async def delete_keyword(ctx: Context, acc: dict, keyword_id: int, ad_group_id: int) -> dict:
    """Delete a keyword from an ad group."""
    return await _delete(
        ctx, acc, f"/v1/keywords/{keyword_id}",
        params={"ad_group_id": ad_group_id},
    )


async def delete_campaign(ctx: Context, acc: dict, campaign_id: int) -> dict:
    """Delete (permanently remove) a campaign."""
    return await _delete(ctx, acc, f"/v1/campaigns/{campaign_id}")


# ─── Negative Keywords ────────────────────────────────────────────────────── #

async def list_negative_keywords(
    ctx: Context, acc: dict, entity_id: int, entity_type: str = "Campaign"
) -> dict:
    """List negative keywords for a campaign or ad group."""
    return await _get(
        ctx, acc, "/v1/negative-keywords",
        entity_id=entity_id, entity_type=entity_type,
    )


async def add_negative_keywords(ctx: Context, acc: dict, data: dict) -> dict:
    """Add negative keywords to a campaign or ad group.

    data: {entity_id, entity_type, keywords: [{text, match_type}]}
    """
    return await _post(ctx, acc, "/v1/negative-keywords", data)


async def remove_negative_keywords(ctx: Context, acc: dict, data: dict) -> dict:
    """Remove negative keywords by ID.

    data: {entity_id, entity_type, keyword_ids: [int]}
    """
    return await _delete(ctx, acc, "/v1/negative-keywords", body=data)
