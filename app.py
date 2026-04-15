"""Microsoft Ads · Extension setup, shared helpers, health check."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from imperal_sdk import Extension, Context
from imperal_sdk.chat import ChatExtension, ActionResult

from msads_providers.helpers import (
    _all_accounts,
    _active_account,
    COLLECTION,
    MSADS_API_URL,
    MSADS_JWT,
    MS_ADS_CLIENT_ID,
)

log = logging.getLogger("microsoft-ads")

# ─── System Prompt ────────────────────────────────────────────────────── #

SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.txt").read_text()

# ─── Extension ────────────────────────────────────────────────────────── #

ext = Extension("microsoft-ads", version="1.0.0")

chat = ChatExtension(
    ext=ext,
    tool_name="tool_msads_chat",
    description=(
        "Microsoft Ads — connect account via OAuth, manage campaigns "
        "(Search/Shopping/PMax/DSA), ad groups, RSA ads, keywords, bid strategies, "
        "performance reports (campaign/keyword/search-terms/budget), keyword research "
        "via AdInsight, bid estimates, budget monitoring, AI performance analysis."
    ),
    system_prompt=SYSTEM_PROMPT,
    model="claude-haiku-4-5-20251001",
)

# ─── Shared error helpers ─────────────────────────────────────────────── #

def _no_account_error() -> ActionResult:
    return ActionResult.error(
        "No Microsoft Ads account connected. Say 'connect Microsoft Ads' to get started.",
        retryable=False,
    )


def _needs_setup_error() -> ActionResult:
    return ActionResult.error(
        "Microsoft Ads authorised but no ad account selected yet. "
        "Say 'setup Microsoft Ads account' to choose your account.",
        retryable=False,
    )


def _needs_reauth_error() -> ActionResult:
    return ActionResult.error(
        "Microsoft Ads authorisation expired. "
        "Say 'reconnect Microsoft Ads' to re-authorise.",
        retryable=False,
    )


async def _get_ready_account(
    ctx: Context, account: str = ""
) -> tuple[Optional[dict], Optional[ActionResult]]:
    """Resolve the active account, returning (acc, None) on success
    or (None, ActionResult.error(...)) when not usable.

    Checks: no accounts → connect error.
            _needs_setup → guide to setup_account.
            _needs_reauth → guide to reconnect.
    """
    acc = await _active_account(ctx, account)
    if not acc:
        return None, _no_account_error()
    if acc.get("_needs_setup"):
        return None, _needs_setup_error()
    if acc.get("_needs_reauth"):
        return None, _needs_reauth_error()
    return acc, None


# ─── Health Check ─────────────────────────────────────────────────────── #

@ext.health_check
async def health(ctx) -> dict:
    """Verify microservice connectivity and report connected accounts."""
    accounts = await _all_accounts(ctx)
    try:
        r = await ctx.http.get(
            f"{MSADS_API_URL}/health",
            headers={"Authorization": f"Bearer {MSADS_JWT}"},
        )
        svc_status = "ok" if r.status_code == 200 else "degraded"
    except Exception:
        svc_status = "unreachable"

    return {
        "status":             "ok" if svc_status == "ok" else "degraded",
        "version":            ext.version,
        "accounts_connected": len(accounts),
        "oauth_configured":   bool(MS_ADS_CLIENT_ID),
        "microservice":       svc_status,
    }
