"""Microsoft Ads · Keyword management and AdInsight research handlers.

Functions: list_keywords, add_keywords, research_keywords, get_bid_estimates.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app import chat, ActionResult, _get_ready_account
import msads_providers.msads_client as api

# ─── Models ──────────────────────────────────────────────────────────── #

class AdGroupIdParams(BaseModel):
    """Identify an ad group."""
    ad_group_id: str = Field(description="Ad group ID")


class KeywordItem(BaseModel):
    """A single keyword to add."""
    text:       str   = Field(description="Keyword text")
    match_type: Literal["Broad", "Phrase", "Exact"] = Field(
        default="Broad",
        description="Match type: Broad (widest reach), Phrase (contains phrase), Exact (exact match)",
    )
    bid:        float = Field(
        default=0.0,
        description="Manual CPC bid (0 = use ad group default bid)",
    )


class AddKeywordsParams(BaseModel):
    """Add keywords to an ad group."""
    ad_group_id: str              = Field(description="Ad group ID")
    keywords:    list[KeywordItem]= Field(description="List of keywords to add (max 1000 per call)")


class ResearchKeywordsParams(BaseModel):
    """Discover keyword ideas via Microsoft AdInsight."""
    seed_keywords: list[str] = Field(
        default=[],
        description="Seed keywords to get ideas from (e.g. ['web hosting', 'vps server'])",
    )
    seed_url:      str       = Field(
        default="",
        description="Website URL to extract keyword ideas from (alternative to seed_keywords)",
    )
    language:      str       = Field(default="English", description="Target language")
    location:      str       = Field(
        default="US",
        description="Target country/location code (e.g. US, GB, DE)",
    )


class BidEstimatesParams(BaseModel):
    """Get position-based bid estimates for a list of keywords."""
    keywords:   list[str] = Field(description="Keywords to estimate bids for")
    match_types: list[Literal["Broad", "Phrase", "Exact"]] = Field(
        default=["Broad"],
        description="Match types to estimate (defaults to Broad)",
    )
    location:   str       = Field(default="US", description="Target location")
    language:   str       = Field(default="English", description="Target language")


# ─── list_keywords ────────────────────────────────────────────────────── #

@chat.function(
    "list_keywords",
    action_type="read",
    description="List all keywords in an ad group with match types, bids, and quality scores.",
)
async def fn_list_keywords(ctx, params: AdGroupIdParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        data = await api.get_keywords(ctx, acc, int(params.ad_group_id))
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)
    keywords = data.get("keywords", [])
    return ActionResult.success(
        data={"keywords": keywords, "total": len(keywords), "ad_group_id": params.ad_group_id},
        summary=f"{len(keywords)} keyword(s) in ad group {params.ad_group_id}.",
    )


# ─── add_keywords ─────────────────────────────────────────────────────── #

@chat.function(
    "add_keywords",
    action_type="write",
    event="keywords.added",
    description="Add one or more keywords to an ad group.",
)
async def fn_add_keywords(ctx, params: AddKeywordsParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    kw_list = [
        {"text": kw.text, "match_type": kw.match_type, "bid": kw.bid or None}
        for kw in params.keywords
    ]
    try:
        result = await api.add_keywords(ctx, acc, {
            "ad_group_id": int(params.ad_group_id),
            "keywords":    kw_list,
        })
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=False)

    added   = result.get("added",  len(kw_list))
    errors  = result.get("errors", [])
    return ActionResult.success(
        data={
            "ad_group_id":    params.ad_group_id,
            "keywords_added": added,
            "keyword_ids":    result.get("keyword_ids", []),
            "errors":         errors,
        },
        summary=f"{added} keyword(s) added to ad group {params.ad_group_id}."
                + (f" ({len(errors)} error(s))." if errors else ""),
    )


# ─── research_keywords ────────────────────────────────────────────────── #

@chat.function(
    "research_keywords",
    action_type="read",
    description=(
        "Discover keyword ideas via Microsoft AdInsight. "
        "Provide either seed_keywords or seed_url (or both). "
        "Returns ideas sorted by relevance with search volume and competition data."
    ),
)
async def fn_research_keywords(ctx, params: ResearchKeywordsParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    if not params.seed_keywords and not params.seed_url:
        return ActionResult.error(
            "Provide at least seed_keywords or seed_url.", retryable=False
        )

    body: dict = {"language": params.language, "location": params.location}
    if params.seed_keywords:
        body["seed_keywords"] = params.seed_keywords
    if params.seed_url:
        body["seed_url"] = params.seed_url

    try:
        result = await api.keyword_ideas(ctx, acc, body)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    ideas = result.get("keyword_ideas", result.get("ideas", []))
    return ActionResult.success(
        data={
            "ideas":    ideas,
            "total":    len(ideas),
            "language": params.language,
            "location": params.location,
        },
        summary=f"{len(ideas)} keyword idea(s) found.",
    )


# ─── get_bid_estimates ────────────────────────────────────────────────── #

@chat.function(
    "get_bid_estimates",
    action_type="read",
    description=(
        "Get required bid estimates for keywords to appear in MainLine1, MainLine, "
        "and FirstPage positions. Use before adding keywords to estimate costs."
    ),
)
async def fn_get_bid_estimates(ctx, params: BidEstimatesParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    try:
        result = await api.bid_estimates(ctx, acc, {
            "keywords":    params.keywords,
            "match_types": params.match_types,
            "location":    params.location,
            "language":    params.language,
        })
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    estimates = result.get("estimates", result.get("keyword_estimates", []))
    return ActionResult.success(
        data={"estimates": estimates, "total": len(estimates)},
        summary=f"Bid estimates for {len(estimates)} keyword(s).",
    )
