"""Microsoft Ads · Performance reports and AI analysis handlers.

Functions: get_performance, get_search_terms, get_budget_status, analyze_performance.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app import chat, ActionResult, _get_ready_account
import msads_providers.msads_client as api

# ─── Helpers ──────────────────────────────────────────────────────────── #

def _default_date_range() -> tuple[str, str]:
    """Return (start, end) for the last 7 days."""
    today = date.today()
    return (today - timedelta(days=7)).isoformat(), today.isoformat()


# ─── Models ──────────────────────────────────────────────────────────── #

class PerformanceParams(BaseModel):
    """Fetch performance metrics for campaigns or ad groups."""
    level: Literal["campaign", "ad-group", "keyword", "summary"] = Field(
        default="campaign",
        description="Report level: campaign, ad-group, keyword, or summary (account total)",
    )
    date_from: str = Field(
        default="",
        description="Start date YYYY-MM-DD (default: 7 days ago)",
    )
    date_to: str = Field(
        default="",
        description="End date YYYY-MM-DD (default: today)",
    )
    campaign_id: Optional[str] = Field(
        default=None,
        description="Filter by campaign ID (optional)",
    )
    aggregation: Literal["Daily", "Weekly", "Monthly", "Summary"] = Field(
        default="Daily",
        description="Time aggregation",
    )


class SearchTermsParams(BaseModel):
    """Fetch the search query report."""
    date_from:   str          = Field(default="", description="Start date YYYY-MM-DD")
    date_to:     str          = Field(default="", description="End date YYYY-MM-DD")
    campaign_id: Optional[str]= Field(default=None, description="Filter by campaign ID")


class AnalyzeParams(BaseModel):
    """AI-powered performance analysis with recommendations."""
    date_from: str = Field(default="", description="Start date YYYY-MM-DD (default: 7 days ago)")
    date_to:   str = Field(default="", description="End date YYYY-MM-DD (default: today)")
    focus:     Literal["general", "keywords", "budget", "ctr", "conversions"] = Field(
        default="general",
        description="Analysis focus area",
    )


# ─── get_performance ──────────────────────────────────────────────────── #

@chat.function(
    "get_performance",
    action_type="read",
    description=(
        "Fetch performance metrics (clicks, impressions, CTR, CPC, spend, conversions). "
        "Supports campaign, ad-group, keyword, or account-level summary."
    ),
)
async def fn_get_performance(ctx, params: PerformanceParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    start, end = (params.date_from, params.date_to) if params.date_from else _default_date_range()

    # Map level to report type
    report_map = {
        "campaign":  "campaign",
        "ad-group":  "ad-group",
        "keyword":   "keyword",
        "summary":   "summary",
    }
    report_type = report_map[params.level]

    try:
        data = await api.get_report(
            ctx, acc, report_type,
            start_date=start,
            end_date=end,
            aggregation=params.aggregation,
            campaign_id=int(params.campaign_id) if params.campaign_id else None,
        )
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    rows = data.get("rows", data.get("data", []))
    return ActionResult.success(
        data={
            "rows":        rows,
            "total":       len(rows),
            "level":       params.level,
            "date_from":   start,
            "date_to":     end,
            "aggregation": params.aggregation,
        },
        summary=f"{len(rows)} row(s) of {params.level} performance ({start} – {end}).",
    )


# ─── get_search_terms ─────────────────────────────────────────────────── #

@chat.function(
    "get_search_terms",
    action_type="read",
    description=(
        "Show what search queries actually triggered your ads. "
        "Essential for finding negative keyword opportunities."
    ),
)
async def fn_get_search_terms(ctx, params: SearchTermsParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    start, end = (params.date_from, params.date_to) if params.date_from else _default_date_range()
    try:
        data = await api.get_report(
            ctx, acc, "search-query",
            start_date=start,
            end_date=end,
            campaign_id=int(params.campaign_id) if params.campaign_id else None,
        )
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    rows = data.get("rows", data.get("data", []))
    return ActionResult.success(
        data={"rows": rows, "total": len(rows), "date_from": start, "date_to": end},
        summary=f"{len(rows)} search term(s) found ({start} – {end}).",
    )


# ─── get_budget_status ────────────────────────────────────────────────── #

@chat.function(
    "get_budget_status",
    action_type="read",
    description="Show today's spend vs budget for all campaigns. Highlights over-pacing campaigns.",
)
async def fn_get_budget_status(ctx) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    today = date.today().isoformat()
    import asyncio as _asyncio

    # Fetch campaign list (required). Fetch today's spend report (optional —
    # CampaignPerformanceReport may fail with Basic Developer Token; we degrade
    # gracefully showing budget without live spend rather than returning an error).
    try:
        campaigns_resp = await api.get_campaigns(ctx, acc)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    spend_rows: list = []
    spend_available = True
    try:
        spend_resp = await api.get_report(
            ctx, acc, "campaign",
            start_date=today, end_date=today,
            aggregation="Summary",
        )
        spend_rows = spend_resp.get("rows", spend_resp.get("data", []))
    except Exception:
        spend_available = False

    camp_list = campaigns_resp.get("campaigns", [])

    # Build spend lookup: CampaignId (PascalCase — Microsoft API) → Spend value
    spend_map: dict[str, float] = {
        str(r.get("CampaignId", r.get("campaign_id", ""))): float(r.get("Spend", r.get("spend", 0)) or 0)
        for r in spend_rows
        if r.get("CampaignId") or r.get("campaign_id")
    }

    result = []
    for c in camp_list:
        cid    = str(c.get("id", c.get("campaign_id", "")))
        budget = float(c.get("daily_budget", c.get("budget_amount", 0)) or 0)
        spend  = spend_map.get(cid, 0.0)
        pct    = round(spend / budget * 100, 1) if budget > 0 else 0.0
        result.append({
            "campaign_id":   cid,
            "campaign_name": c.get("name", ""),
            "status":        c.get("status", ""),
            "daily_budget":  budget,
            "today_spend":   spend,
            "pct_used":      pct,
            "alert":         pct >= 90,
        })

    result.sort(key=lambda x: x["pct_used"], reverse=True)
    alerts = [r for r in result if r["alert"]]

    note = " (live spend unavailable — today's pct_used may be inaccurate)" if not spend_available else ""
    return ActionResult.success(
        data={"campaigns": result, "alerts": alerts, "date": today, "spend_available": spend_available},
        summary=(
            f"Budget status: {len(alerts)} campaign(s) near limit.{note}"
            if alerts else
            f"Budget status: {len(result)} campaign(s).{note}"
        ),
    )


# ─── analyze_performance ──────────────────────────────────────────────── #

@chat.function(
    "analyze_performance",
    action_type="read",
    description=(
        "AI-powered analysis of campaign performance with specific recommendations. "
        "Identifies underperformers, keyword opportunities, and budget optimisations."
    ),
)
async def fn_analyze_performance(ctx, params: AnalyzeParams) -> ActionResult:
    acc, err = await _get_ready_account(ctx)
    if err:
        return err

    start, end = (params.date_from, params.date_to) if params.date_from else _default_date_range()

    await ctx.progress(10, "Fetching performance data…")
    try:
        camp_data = await api.get_report(ctx, acc, "campaign",  start_date=start, end_date=end, aggregation="Summary")
        kw_data   = await api.get_report(ctx, acc, "keyword",   start_date=start, end_date=end, aggregation="Summary")
        sq_data   = await api.get_report(ctx, acc, "search-query", start_date=start, end_date=end)
    except Exception as exc:
        return ActionResult.error(str(exc)[:200], retryable=True)

    await ctx.progress(60, "Running AI analysis…")

    camp_rows = camp_data.get("rows", camp_data.get("data", []))
    kw_rows   = kw_data.get("rows", kw_data.get("data", []))
    sq_rows   = sq_data.get("rows", sq_data.get("data", []))[:30]  # top 30 search terms

    prompt = (
        f"Analyse this Microsoft Advertising account performance "
        f"from {start} to {end}. Focus: {params.focus}.\n\n"
        f"CAMPAIGN DATA (summary):\n{camp_rows!r:.3000}\n\n"
        f"KEYWORD DATA (top by spend):\n{kw_rows!r:.2000}\n\n"
        f"SEARCH TERMS SAMPLE:\n{sq_rows!r:.1500}\n\n"
        "Provide:\n"
        "1. 3 key insights (what's working, what's not, with specific numbers)\n"
        "2. Top 3 actionable recommendations with exact values to change\n"
        "3. Keywords to pause or lower bids (CTR < 1% AND spend > average)\n"
        "4. Negative keyword suggestions from irrelevant search terms\n"
        "5. Budget reallocation suggestion if any campaign is limited\n\n"
        "Be specific. Use actual numbers from the data."
    )
    analysis = await ctx.ai.complete(prompt=prompt, model="claude-sonnet-4-6")

    await ctx.progress(100, "Analysis complete.")
    return ActionResult.success(
        data={
            "analysis":  analysis.text,
            "date_from": start,
            "date_to":   end,
            "focus":     params.focus,
            "campaigns": camp_rows,
        },
        summary=f"AI analysis complete for {start} – {end}.",
    )
