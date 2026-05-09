from datetime import datetime, timezone
from typing import Any


def normalize_manual_trigger(payload: dict[str, Any], workflow_id: str) -> dict[str, Any]:
    """
    Wrap a raw manual trigger payload in a standard TriggerEnvelope.
    Returns: {source, event_id, timestamp, data}
    """
    import uuid
    return {
        "source": "manual",
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": payload,
    }


def normalize_gmail_trigger(raw_message: dict[str, Any]) -> dict[str, Any]:
    """Import from gmail trigger module — re-exported here for unified interface."""
    from app.integrations.gmail.trigger import normalize_message
    return normalize_message(raw_message)


def envelope_to_input_text(envelope: dict[str, Any]) -> str:
    """
    Convert a TriggerEnvelope to a flat text string for LLM input.
    Handles both Gmail and manual trigger formats.
    """
    data = envelope.get("data", {})
    source = envelope.get("source", "unknown")

    if source == "gmail":
        parts = []
        if data.get("subject"):
            parts.append(f"Subject: {data['subject']}")
        if data.get("from"):
            parts.append(f"From: {data['from']}")
        if data.get("snippet"):
            parts.append(f"Snippet: {data['snippet']}")
        if data.get("body"):
            body = data["body"][:2000]  # Limit to 2000 chars
            parts.append(f"Body:\n{body}")
        return "\n".join(parts)

    # Manual or unknown: serialize all fields
    lines = []
    for key, value in data.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)