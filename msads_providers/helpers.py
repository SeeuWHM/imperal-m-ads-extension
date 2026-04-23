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

# ─── Microsoft Ads location IDs ──────────────────────────────────────── #
# Maps ISO codes / names → Microsoft Ads location ID lists.
# Full list: https://docs.microsoft.com/en-us/advertising/guides/geographical-location-codes
_MS_LOCATION_IDS: dict[str, list[int]] = {
    "US": [190], "USA": [190],
    "UK": [91],  "GB": [91],
    "CA": [32],  "CANADA": [32],
    "AU": [13],  "AUSTRALIA": [13],
    "DE": [58],  "GERMANY": [58],
    "FR": [82],  "FRANCE": [82],
    "IN": [176], "INDIA": [176],
    "SG": [252], "SINGAPORE": [252],
    "NL": [170], "NETHERLANDS": [170],
    "ES": [217], "SPAIN": [217],
    "IT": [118], "ITALY": [118],
    "BR": [37],  "BRAZIL": [37],
    "MX": [161], "MEXICO": [161],
    "JP": [129], "JAPAN": [129],
    "NZ": [172], "NEW ZEALAND": [172],
    "ZA": [214], "SOUTH AFRICA": [214],
    "AE": [6],   "UAE": [6],
}


def _to_location_ids(location: str) -> list[int]:
    """Translate a country code or name to Microsoft Ads location ID list.

    Returns [190] (United States) when the code is unknown — safe default.
    """
    return _MS_LOCATION_IDS.get(location.upper().strip(), [190])


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
