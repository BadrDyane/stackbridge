import base64
import re
from datetime import datetime, timezone
from typing import Any

import httpx

MESSAGES_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
HISTORY_URL = "https://gmail.googleapis.com/gmail/v1/users/me/history"


def _decode_body(payload: dict) -> str:
    """Recursively extract and decode the email body from Gmail payload."""
    if payload.get("body", {}).get("data"):
        data = payload["body"]["data"]
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

    # Fallback: try html part
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/html":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

    return ""


def _get_header(headers: list[dict], name: str) -> str:
    """Extract a header value by name (case-insensitive)."""
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def normalize_message(raw_message: dict) -> dict:
    """
    Convert a raw Gmail API message object into a standard TriggerEnvelope.
    Returns: {source, event_id, timestamp, data: {subject, from, to, date, snippet, body}}
    """
    payload = raw_message.get("payload", {})
    headers = payload.get("headers", [])

    internal_date_ms = int(raw_message.get("internalDate", 0))
    timestamp = datetime.fromtimestamp(internal_date_ms / 1000, tz=timezone.utc).isoformat()

    return {
        "source": "gmail",
        "event_id": raw_message["id"],
        "timestamp": timestamp,
        "data": {
            "message_id": raw_message["id"],
            "thread_id": raw_message.get("threadId", ""),
            "subject": _get_header(headers, "subject"),
            "from": _get_header(headers, "from"),
            "to": _get_header(headers, "to"),
            "date": _get_header(headers, "date"),
            "snippet": raw_message.get("snippet", ""),
            "body": _decode_body(payload),
        },
    }


async def get_new_messages(
    access_token: str,
    history_id: str,
) -> tuple[list[dict], str]:
    """
    Fetch new messages since the given historyId using Gmail History API.
    Returns (list of raw message objects, latest historyId).
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            HISTORY_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "startHistoryId": history_id,
                "historyTypes": "messageAdded",
                "labelIds": "INBOX",
            },
        )

        if resp.status_code == 404:
            # historyId is too old — return empty, caller must reseed
            return [], history_id

        resp.raise_for_status()
        data = resp.json()

    latest_history_id = data.get("historyId", history_id)
    history_records = data.get("history", [])

    message_ids: list[str] = []
    for record in history_records:
        for added in record.get("messagesAdded", []):
            msg_id = added.get("message", {}).get("id")
            if msg_id and msg_id not in message_ids:
                message_ids.append(msg_id)

    if not message_ids:
        return [], latest_history_id

    # Fetch full message details for each new message
    messages = []
    async with httpx.AsyncClient() as client:
        for msg_id in message_ids:
            resp = await client.get(
                f"{MESSAGES_URL}/{msg_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"format": "full"},
            )
            if resp.status_code == 200:
                messages.append(resp.json())

    return messages, latest_history_id


def apply_filter(envelope: dict, gmail_filter: str | None) -> bool:
    """
    Apply a simple Gmail query filter to a normalized envelope.
    Supports: to:email, from:email, subject:text
    Returns True if the message passes the filter (should be processed).
    """
    if not gmail_filter:
        return True

    data = envelope.get("data", {})
    filter_lower = gmail_filter.lower().strip()

    # Parse simple key:value filters
    to_match = re.search(r"to:(\S+)", filter_lower)
    from_match = re.search(r"from:(\S+)", filter_lower)
    subject_match = re.search(r"subject:(\S+)", filter_lower)

    if to_match:
        if to_match.group(1) not in data.get("to", "").lower():
            return False
    if from_match:
        if from_match.group(1) not in data.get("from", "").lower():
            return False
    if subject_match:
        if subject_match.group(1) not in data.get("subject", "").lower():
            return False

    return True