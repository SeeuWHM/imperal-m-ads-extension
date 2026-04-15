"""Microsoft Ads · Shared constants and account helpers."""
from __future__ import annotations

import base64
import json
import os
from typing import Optional

from imperal_sdk import Context

# ─── OAuth constants ──────────────────────────────────────────────────── #

MS_ADS_AUTH_URL     = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
MS_ADS_TOKEN_URL    = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MS_ADS_SCOPE        = "https://ads.microsoft.com/msads.manage offline_access"

MS_ADS_CLIENT_ID     = os.getenv("MS_ADS_CLIENT_ID",     "")
MS_ADS_CLIENT_SECRET = os.getenv("MS_ADS_CLIENT_SECRET", "")
MS_ADS_REDIRECT_URI  = os.getenv(
    "MS_ADS_REDIRECT_URI",
    "https://auth.imperal.io/v1/oauth/microsoft-ads/callback",
)

# ─── Storage ─────────────────────────────────────────────────────────── #

COLLECTION = "msads_accounts"  # ext_store collection name

# ─── Microservice ─────────────────────────────────────────────────────── #

MSADS_API_URL = os.getenv("MSADS_API_URL", "https://api.webhostmost.com/microsoft-ads")
MSADS_JWT     = os.getenv("MSADS_JWT",     "")


# ─── OAuth state ─────────────────────────────────────────────────────── #

def _oauth_state(ctx: Context) -> str:
    """Encode user identity as base64url JSON for the OAuth state parameter.
    Auth Gateway decodes this in the /v1/oauth/microsoft-ads/callback handler.
    """
    payload = {
        "user_id":   str(ctx.user.id),
        "tenant_id": getattr(ctx.user, "tenant_id", "default"),
        "provider":  "microsoft-ads",
    }
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


# ─── Account helpers ─────────────────────────────────────────────────── #

async def _all_accounts(ctx: Context) -> list[dict]:
    """Return all msads_accounts documents for the current user."""
    page = await ctx.store.query(COLLECTION)
    return [{"doc_id": d.id, **d.data} for d in page.data]


async def _active_account(ctx: Context, account: str = "") -> Optional[dict]:
    """Return the active (or specified) account dict, or None if not found."""
    page = await ctx.store.query(COLLECTION)
    if not page.data:
        return None

    if account:
        for d in page.data:
            if (d.id == account
                    or d.data.get("account_id") == account
                    or d.data.get("account_name") == account):
                return {"doc_id": d.id, **d.data}
        return None

    # Return the document marked is_active, fall back to first
    for d in page.data:
        if d.data.get("is_active"):
            return {"doc_id": d.id, **d.data}
    return {"doc_id": page.data[0].id, **page.data[0].data}
