"""Microsoft Ads · Shared panel UI helpers."""
from __future__ import annotations

from datetime import date, timedelta
from urllib.parse import urlencode

from imperal_sdk import ui
from msads_providers.helpers import (
    MS_ADS_AUTH_URL, MS_ADS_CLIENT_ID, MS_ADS_REDIRECT_URI,
    MS_ADS_SCOPE, _oauth_state,
)

# ─── Date range options ───────────────────────────────────────────────── #

DATE_OPTS = [
    {"value": "TODAY",        "label": "Today"},
    {"value": "LAST_7_DAYS",  "label": "Last 7 days"},
    {"value": "LAST_30_DAYS", "label": "Last 30 days"},
    {"value": "THIS_MONTH",   "label": "This month"},
    {"value": "LAST_MONTH",   "label": "Last month"},
]


def date_range(preset: str) -> tuple[str, str]:
    """Convert preset to (start_date, end_date) ISO strings."""
    today = date.today()
    if preset == "TODAY":
        return str(today), str(today)
    if preset == "LAST_7_DAYS":
        return str(today - timedelta(days=6)), str(today)
    if preset == "THIS_MONTH":
        return str(today.replace(day=1)), str(today)
    if preset == "LAST_MONTH":
        first = today.replace(day=1)
        last_prev = first - timedelta(days=1)
        return str(last_prev.replace(day=1)), str(last_prev)
    return str(today - timedelta(days=29)), str(today)  # LAST_30_DAYS default


# ─── Formatters ───────────────────────────────────────────────────────── #

def fmt_currency(amount, currency: str = "$") -> str:
    try:
        return f"{currency}{float(amount):.2f}"
    except (TypeError, ValueError):
        return f"{currency}0.00"


def fmt_pct(value, decimals: int = 1) -> str:
    try:
        return f"{float(value):.{decimals}f}%"
    except (TypeError, ValueError):
        return "0.0%"


def fmt_number(value) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


# ─── Badge helpers ────────────────────────────────────────────────────── #

_CAMPAIGN_COLORS = {
    "Active":  "green",
    "Paused":  "gray",
    "Deleted": "red",
    "Draft":   "yellow",
}


def campaign_badge(status: str) -> ui.Badge:
    return ui.Badge(label=status or "—", color=_CAMPAIGN_COLORS.get(status, "gray"))


# ─── Connection state views ───────────────────────────────────────────── #

def _build_oauth_url(ctx) -> str:
    if not MS_ADS_CLIENT_ID:
        return ""
    return MS_ADS_AUTH_URL + "?" + urlencode({
        "client_id":     MS_ADS_CLIENT_ID,
        "response_type": "code",
        "redirect_uri":  MS_ADS_REDIRECT_URI,
        "scope":         MS_ADS_SCOPE,
        "response_mode": "query",
        "state":         _oauth_state(ctx),
    })


def not_connected_view(ctx) -> ui.UINode:
    url = _build_oauth_url(ctx)
    return ui.Stack([
        ui.Header(text="Microsoft Ads", subtitle="Not connected"),
        ui.Divider(),
        ui.Text(
            "Connect your Microsoft Advertising account to manage campaigns via AI.",
            variant="caption",
        ),
        ui.Button(
            "Connect Microsoft Ads",
            variant="primary",
            icon="ExternalLink",
            full_width=True,
            on_click=ui.Open(url) if url else ui.Send("Connect Microsoft Ads"),
        ),
    ])


def needs_setup_view(display_name: str = "") -> ui.UINode:
    who = f" as {display_name}" if display_name else ""
    return ui.Stack([
        ui.Alert(
            type="info",
            message=f"Signed in{who} with Microsoft. Select your ad account to continue.",
        ),
        ui.Button(
            "Setup account",
            variant="primary",
            full_width=True,
            on_click=ui.Send("Setup my Microsoft Ads account"),
        ),
        ui.Divider(),
        ui.Button(
            "Wrong account? Disconnect",
            variant="ghost",
            full_width=True,
            on_click=ui.Send("Disconnect Microsoft Ads account"),
        ),
    ])


def error_view(msg: str, ctx=None) -> ui.UINode:
    url = _build_oauth_url(ctx) if ctx else ""
    return ui.Stack([
        ui.Alert(type="error", message=msg[:200]),
        ui.Button(
            "Reconnect",
            variant="primary",
            full_width=True,
            on_click=ui.Open(url) if url else ui.Send("Reconnect Microsoft Ads"),
        ),
    ])
