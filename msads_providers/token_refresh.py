"""Microsoft Ads · Token refresh helpers.

Mirrors the pattern from mail/providers/token_refresh.py.
Token exchange goes directly to Microsoft — no microservice involved.
"""
from __future__ import annotations

import logging
import time

from imperal_sdk import Context

from .helpers import (
    COLLECTION,
    MS_ADS_CLIENT_ID,
    MS_ADS_CLIENT_SECRET,
    MS_ADS_SCOPE,
    MS_ADS_TOKEN_URL,
)

log = logging.getLogger("microsoft-ads.token")

# ─── Refresh ─────────────────────────────────────────────────────────── #

async def _refresh_msads_token(ctx: Context, acc: dict) -> dict:
    """Exchange the stored refresh_token for a new access_token.

    On success: updates ctx.store and returns updated acc dict.
    On failure (400 = refresh_token expired): sets _needs_reauth=True in store.
    Never raises — returns acc unchanged on transient errors.
    """
    resp = await ctx.http.post(MS_ADS_TOKEN_URL, data={
        "grant_type":    "refresh_token",
        "client_id":     MS_ADS_CLIENT_ID,
        "client_secret": MS_ADS_CLIENT_SECRET,
        "refresh_token": acc["refresh_token"],
        "scope":         MS_ADS_SCOPE,
    })

    if resp.status_code != 200:
        log.warning(
            "Microsoft Ads token refresh failed: %s — %s",
            resp.status_code,
            resp.text()[:200],
        )
        if resp.status_code == 400:
            # Refresh token expired — user must re-authorise
            acc["_needs_reauth"] = True
            doc_id = acc.get("doc_id")
            if doc_id:
                try:
                    await ctx.store.update(COLLECTION, doc_id, {"_needs_reauth": True})
                except Exception:
                    pass
        return acc

    tokens = resp.json()
    acc["access_token"] = tokens["access_token"]
    acc["expires_at"]   = int(time.time()) + tokens.get("expires_in", 3600)
    # Microsoft may rotate the refresh_token; persist it if returned
    if "refresh_token" in tokens:
        acc["refresh_token"] = tokens["refresh_token"]
    acc.pop("_needs_reauth", None)

    doc_id = acc.pop("doc_id")
    await ctx.store.update(COLLECTION, doc_id, {k: v for k, v in acc.items()})
    acc["doc_id"] = doc_id
    return acc


async def _refresh_token_if_needed(ctx: Context, acc: dict) -> dict:
    """Refresh access_token if it expires within 120 seconds."""
    if acc.get("expires_at", 0) > time.time() + 120:
        return acc
    return await _refresh_msads_token(ctx, acc)
