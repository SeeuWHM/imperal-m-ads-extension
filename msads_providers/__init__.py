"""Microsoft Ads extension providers — exports."""
from __future__ import annotations

from .helpers import _all_accounts, _active_account, COLLECTION
from .token_refresh import _refresh_token_if_needed
from .msads_client import (
    list_customers_for_token,
    get_account_info,
    get_campaigns,
    get_campaign,
    create_campaign,
    update_campaign,
    get_ad_groups,
    create_ad_group,
    get_ads,
    create_ad,
    update_ad,
    get_keywords,
    add_keywords,
    keyword_ideas,
    bid_estimates,
    get_report,
)

__all__ = [
    "_all_accounts", "_active_account", "COLLECTION",
    "_refresh_token_if_needed",
    "list_customers_for_token", "get_account_info",
    "get_campaigns", "get_campaign", "create_campaign", "update_campaign",
    "get_ad_groups", "create_ad_group",
    "get_ads", "create_ad", "update_ad",
    "get_keywords", "add_keywords",
    "keyword_ideas", "bid_estimates",
    "get_report",
]
