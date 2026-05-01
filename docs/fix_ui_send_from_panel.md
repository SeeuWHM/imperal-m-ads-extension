# Bug Report: `ui.Send` from panel buttons does not trigger chat

> **Status: WORKED AROUND** — All affected buttons replaced with `ui.Call` in v1.1.0. Platform fix still pending.

**SDK:** `1.6.2` (reported) | **Extension:** `microsoft-ads` | **Branch:** `ui/campaign-detail-split`

---

## Summary

Three buttons in `panels_campaign_detail.py` use `ui.Send(...)` as `on_click`. All three are completely silent when clicked — no message appears in chat, no error, no notification.

`ui.Call(...)` buttons in the same panel work correctly.

---

## Affected buttons

**1. "AI Analyse" button** (`panels_campaign_detail.py`, line ~97)
```python
ui.Button("AI Analyse", icon="Sparkles", variant="ghost",
          on_click=ui.Send(f"Analyse the performance of campaign '{camp_name}' (id: {campaign_id})"))
```

**2. "Keywords" action on ad group list items** (`panels_campaign_detail.py`, line ~222)
```python
{"icon": "List", "label": "Keywords",
 "on_click": ui.Send(f"Show keywords in ad group '{ag_name}' (id: {agid})")}
```

**3. "Ads" action on ad group list items** (`panels_campaign_detail.py`, line ~227)
```python
{"icon": "FileText", "label": "Ads",
 "on_click": ui.Send(f"Show ads in ad group '{ag_name}' (id: {agid})")}
```

---

## Expected behaviour

Message is sent to chat → LLM calls the appropriate function → formatted result shown in chat.

## Actual behaviour

Button click does nothing. Silent.

---

## What works in the same panel

```python
# These all work fine:
ui.Call("pause_campaign", campaign_id=campaign_id)
ui.Call("__panel__campaign_detail", campaign_id=cid, mode="create_ag")
```

---

## Hypothesis

`ui.Send` requires an active chat session. When triggered from a panel with no active chat, the message is dropped silently by the platform.

---

## Desired fix

`ui.Send` from a panel button should reliably deliver the message to chat, activating the chat session if needed.
