"""Microsoft Ads · Account management handlers.

Functions: connect, status, setup_account, switch_account, disconnect.
"""
from __future__ import annotations

from urllib.parse import urlencode

from pydantic import BaseModel, Field

from app import chat, ActionResult, _get_ready_account, _no_account_error
from msads_providers.helpers import (
    _all_accounts,
    _active_account,
    COLLECTION,
    MS_ADS_AUTH_URL,
    MS_ADS_CLIENT_ID,
    MS_ADS_REDIRECT_URI,
    MS_ADS_SCOPE,
    _oauth_state,
)
from msads_providers.msads_client import list_customers_for_token

# ─── Models ──────────────────────────────────────────────────────────── #

class SetupAccountParams(BaseModel):
    """Select a Microsoft Ads account after OAuth authorisation."""
    account_id: str = Field(
        description="Microsoft Ads Account ID to activate (numeric, e.g. 187176890)"
    )


class AccountParams(BaseModel):
    """Target a specific account by ID or name."""
    account: str = Field(description="Account ID or account name")


# ─── connect ─────────────────────────────────────────────────────────── #

@chat.function(
    "connect",
    action_type="write",
    event="account_connected",
    description=(
        "Connect a Microsoft Ads account via OAuth. "
        "Checks if already connected first. Returns an authorisation URL."
    ),
)
async def fn_connect(ctx) -> ActionResult:
    accounts = await _all_accounts(ctx)

    # Already fully connected
    ready = [a for a in accounts if a.get("customer_id") and not a.get("_needs_reauth")]
    if ready:
        active = next((a for a in ready if a.get("is_active")), ready[0])
        return ActionResult.success(
            data={
                "already_connected": True,
                "account_name":      active.get("account_name", ""),
                "account_id":        active.get("account_id",   ""),
                "total_accounts":    len(ready),
            },
            summary=f"Already connected: {active.get('account_name', active.get('account_id'))}",
        )

    # Tokens stored but account not selected yet
    pending = [a for a in accounts if a.get("_needs_setup")]
    if pending:
        return ActionResult.success(
            data={"needs_setup": True},
            summary="Authorised — say 'setup Microsoft Ads account' to select your ad account.",
        )

    if not MS_ADS_CLIENT_ID:
        return ActionResult.error(
            "Microsoft Ads OAuth is not configured on this platform. "
            "Contact your administrator.",
            retryable=False,
        )

    url = MS_ADS_AUTH_URL + "?" + urlencode({
        "client_id":     MS_ADS_CLIENT_ID,
        "response_type": "code",
        "redirect_uri":  MS_ADS_REDIRECT_URI,
        "scope":         MS_ADS_SCOPE,
        "response_mode": "query",
        "state":         _oauth_state(ctx),
    })
    return ActionResult.success(
        data={
            "auth_url":    url,
            "instruction": "Open the link and sign in with your Microsoft account to grant access.",
        },
        summary="Microsoft Ads OAuth URL ready — open it to authorise access.",
    )


# ─── status ──────────────────────────────────────────────────────────── #

@chat.function(
    "status",
    action_type="read",
    description="Show all connected Microsoft Ads accounts and today's summary stats.",
)
async def fn_status(ctx) -> ActionResult:
    accounts = await _all_accounts(ctx)
    if not accounts:
        return ActionResult.success(
            data={"connected": False, "accounts": [], "total": 0},
            summary="No Microsoft Ads account connected.",
        )

    skeleton_data = await ctx.skeleton.get("msads_account") or {}
    today = skeleton_data.get("today", {})

    result = [
        {
            "account_id":   a.get("account_id",   ""),
            "account_name": a.get("account_name", ""),
            "currency":     a.get("currency",     ""),
            "is_active":    a.get("is_active",    False),
            "_needs_setup": a.get("_needs_setup", False),
            "_needs_reauth":a.get("_needs_reauth",False),
        }
        for a in accounts
    ]
    return ActionResult.success(
        data={
            "connected": True,
            "accounts":  result,
            "total":     len(result),
            "today":     today,
        },
        summary=f"{len(result)} Microsoft Ads account(s) connected.",
    )


# ─── setup_account ───────────────────────────────────────────────────── #

@chat.function(
    "setup_account",
    action_type="write",
    event="account_connected",
    description=(
        "After OAuth, discover accessible Microsoft Ads accounts and activate one. "
        "Call this after 'connect' to complete the setup. "
        "If account_id is unknown, call without it to list all available accounts."
    ),
)
async def fn_setup_account(ctx, params: SetupAccountParams) -> ActionResult:
    accounts = await _all_accounts(ctx)
    pending  = next((a for a in accounts if a.get("_needs_setup")), None)
    if not pending:
        # No pending setup — maybe already done or not authorised yet
        return ActionResult.error(
            "No pending authorisation found. "
            "Say 'connect Microsoft Ads' first.",
            retryable=False,
        )

    access_token = pending.get("access_token", "")
    customers    = await list_customers_for_token(ctx, access_token)

    if not customers:
        return ActionResult.error(
            "No Microsoft Ads accounts found for this Microsoft account. "
            "Ensure you have access to at least one Microsoft Advertising account.",
            retryable=False,
        )

    # If no account_id given, list all and ask user to specify
    if not params.account_id:
        return ActionResult.success(
            data={"available_accounts": customers, "needs_selection": True},
            summary=f"Found {len(customers)} account(s). Specify account_id to activate.",
        )

    target = next(
        (c for c in customers if str(c["account_id"]) == str(params.account_id)), None
    )
    if not target:
        return ActionResult.error(
            f"Account ID {params.account_id} not found. "
            f"Available: "
            + ", ".join(f"{c['account_name']} ({c['account_id']})" for c in customers),
            retryable=False,
        )

    try:
        await ctx.store.update(COLLECTION, pending["doc_id"], {
            **{k: v for k, v in pending.items() if k != "doc_id"},
            "customer_id":  str(target["customer_id"]),
            "account_id":   str(target["account_id"]),
            "account_name": target["account_name"],
            "currency":     target.get("currency", "USD"),
            "_needs_setup": False,
        })
    except Exception as e:
        return ActionResult.error(f"Failed to save account: {str(e)[:120]}", retryable=False)
    return ActionResult.success(
        data={
            "account_id":          target["account_id"],
            "account_name":        target["account_name"],
            "currency":            target.get("currency", "USD"),
            "available_accounts":  customers,
        },
        summary=f"Microsoft Ads account '{target['account_name']}' activated.",
    )


# ─── switch_account ───────────────────────────────────────────────────── #

@chat.function(
    "switch_account",
    action_type="write",
    event="account_switched",
    description="Switch the active Microsoft Ads account.",
)
async def fn_switch_account(ctx, params: AccountParams) -> ActionResult:
    docs = await ctx.store.query(COLLECTION)
    if not docs:
        return _no_account_error()

    target = next(
        (d for d in docs
         if d.id == params.account
         or d.get("account_id")   == params.account
         or d.get("account_name") == params.account),
        None,
    )
    if not target:
        available = [d.get("account_name", d.get("account_id")) for d in docs]
        return ActionResult.error(
            f"Account not found. Available: {available}", retryable=False
        )

    for d in docs:
        is_target = d.id == target.id
        if d.get("is_active") != is_target:
            await ctx.store.update(
                COLLECTION, d.id,
                {**d.data, "is_active": is_target},
            )

    return ActionResult.success(
        data={"switched": True, "account_id": target.get("account_id"),
              "account_name": target.get("account_name")},
        summary=f"Switched to {target.get('account_name', target.get('account_id'))}.",
    )


# ─── disconnect ───────────────────────────────────────────────────────── #

@chat.function(
    "disconnect",
    action_type="destructive",
    event="account_disconnected",
    description="Remove a connected Microsoft Ads account and revoke its tokens.",
)
async def fn_disconnect(ctx, params: AccountParams) -> ActionResult:
    docs = await ctx.store.query(COLLECTION)
    target = next(
        (d for d in docs
         if d.id == params.account
         or d.get("account_id")   == params.account
         or d.get("account_name") == params.account),
        None,
    )
    if not target:
        return ActionResult.error("Account not found.", retryable=False)

    await ctx.store.delete(COLLECTION, target.id)
    return ActionResult.success(
        data={
            "disconnected": True,
            "account_id":   target.get("account_id", ""),
            "account_name": target.get("account_name", ""),
            "remaining":    len(docs) - 1,
        },
        summary=f"Disconnected {target.get('account_name', target.get('account_id'))}.",
    )
