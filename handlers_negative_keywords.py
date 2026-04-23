"""Microsoft Ads · Negative keyword management handlers.

Functions: list_negative_keywords, add_negative_keywords, remove_negative_keywords.

Negative keywords prevent ads from showing for irrelevant searches.
Campaign-level negatives block ALL ad groups; ad-group-level block only that group.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app import chat, ActionResult, _get_ready_account
import msads_providers.msads_client as api

# ─── Models ──────────────────────────────────────────────────────────────── #


class NegativeKeywordItem(BaseModel):
    """A single negative keyword to add."""
    text:       str = Field(description="Negative keyword text (e.g. 'free hosting')")
    match_type: Literal["Phrase", "Exact"] = Field(
        default="Phrase",
        description=(
            "Phrase = blocks queries containing this phrase. "
            "Exact = blocks only the exact query."
        ),
    )


class ListNegativeKeywordsParams(BaseModel):
    """List negative keywords for a campaign or ad group."""
    entity_id:   str                             = Field(description="Campaign ID or Ad Group ID")
    entity_type: Literal["Campaign", "AdGroup"]  = Field(
        default="Campaign",
        description="Campaign (blocks all ad groups) or AdGroup (blocks specific group only)",
    )


class AddNegativeKeywordsParams(BaseModel):
    """Add negative keywords to a campaign or ad group."""
    entity_id:   str                            = Field(description="Campaign ID or Ad Group ID")
    entity_type: Literal["Campaign", "AdGroup"] = Field(
        default="Campaign",
        description="Campaign (blocks all ad groups) or AdGroup (blocks specific group only)",
    )
    keywords: list[NegativeKeywordItem] = Field(
        description="Negative keywords to add (max 20 000 per campaign, 10 000 per ad group)",
    )


class RemoveNegativeKeywordsParams(BaseModel):
    """Remove negative keywords by their IDs."""
    entity_id:   str                            = Field(description="Campaign ID or Ad Group ID")
    entity_type: Literal["Campaign", "AdGroup"] = Field(
        default="Campaign",
        description="Campaign or AdGroup",
    )
    keyword_ids: list[str] = Field(
        description="IDs of negative keywords to delete (get from list_negative_keywords)",
    )


# ─── list_negative_keywords ──────────────────────────────────────────────── #

@chat.function(
    "list_negative_keywords",
    action_type="read",
    description=(
        "List all negative keywords for a campaign or ad group. "
        "Campaign-level negatives block all ad groups in that campaign."
    ),
)
async def fn_list_negative_keywords(ctx, params: ListNegativeKeywordsParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        data = await api.list_negative_keywords(
            ctx, acc, int(params.entity_id), params.entity_type
        )
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    keywords = data.get("negative_keywords", [])
    return ActionResult.success(
        data={
            "negative_keywords": keywords,
            "total":             len(keywords),
            "entity_id":         params.entity_id,
            "entity_type":       params.entity_type,
        },
        summary=f"{len(keywords)} negative keyword(s) on {params.entity_type} {params.entity_id}.",
    )


# ─── add_negative_keywords ───────────────────────────────────────────────── #

@chat.function(
    "add_negative_keywords",
    action_type="write",
    event="negative_keywords.added",
    description=(
        "Add negative keywords to a campaign or ad group to prevent ads from "
        "showing for irrelevant searches. "
        "Use entity_type='Campaign' to block for all ad groups in the campaign."
    ),
)
async def fn_add_negative_keywords(ctx, params: AddNegativeKeywordsParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    keywords_data = [{"text": kw.text, "match_type": kw.match_type} for kw in params.keywords]
    try:
        result = await api.add_negative_keywords(ctx, acc, {
            "entity_id":   int(params.entity_id),
            "entity_type": params.entity_type,
            "keywords":    keywords_data,
        })
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=False)

    inner  = result.get("result", result)
    added  = inner.get("added", len(keywords_data))
    return ActionResult.success(
        data={
            "entity_id":   params.entity_id,
            "entity_type": params.entity_type,
            "added":       added,
            "keywords":    keywords_data,
        },
        summary=f"{added} negative keyword(s) added to {params.entity_type} {params.entity_id}.",
    )


# ─── remove_negative_keywords ────────────────────────────────────────────── #

@chat.function(
    "remove_negative_keywords",
    action_type="destructive",
    event="negative_keywords.removed",
    description=(
        "Remove negative keywords by their IDs from a campaign or ad group. "
        "Get IDs from list_negative_keywords first."
    ),
)
async def fn_remove_negative_keywords(ctx, params: RemoveNegativeKeywordsParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err
    try:
        await api.remove_negative_keywords(ctx, acc, {
            "entity_id":   int(params.entity_id),
            "entity_type": params.entity_type,
            "keyword_ids": [int(kid) for kid in params.keyword_ids],
        })
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=False)

    return ActionResult.success(
        data={
            "entity_id":    params.entity_id,
            "entity_type":  params.entity_type,
            "removed":      len(params.keyword_ids),
            "keyword_ids":  params.keyword_ids,
        },
        summary=f"{len(params.keyword_ids)} negative keyword(s) removed from {params.entity_type} {params.entity_id}.",
    )
