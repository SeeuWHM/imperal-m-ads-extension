"""Microsoft Ads · Shared panel UI helpers."""
from __future__ import annotations

from datetime import date, timedelta

from imperal_sdk import ui

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

def not_connected_view() -> ui.UINode:
    return ui.Stack([
        ui.Empty(
            message="No Microsoft Ads account connected.",
            icon="TrendingUp",
            action=ui.Send("Connect Microsoft Ads"),
        ),
    ])


def needs_setup_view() -> ui.UINode:
    return ui.Stack([
        ui.Alert(type="warn",
                 message="Authorised! Select your ad account to continue."),
        ui.Button("Setup account", variant="primary", full_width=True,
                  on_click=ui.Send("Setup my Microsoft Ads account")),
    ])


def error_view(msg: str) -> ui.UINode:
    return ui.Stack([
        ui.Alert(type="error", message=msg[:200]),
        ui.Button("Reconnect", variant="ghost",
                  on_click=ui.Send("Reconnect Microsoft Ads")),
    ])
