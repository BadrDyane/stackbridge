import asyncio
import re
from typing import Any

import httpx

SLACK_POST_URL = "https://slack.com/api/chat.postMessage"


def _render_template(template: str, ai_output: dict[str, Any]) -> str:
    """
    Replace {field_name} placeholders with values from ai_output.
    Unknown placeholders are replaced with empty string with a warning.
    """
    def replacer(match: re.Match) -> str:
        field = match.group(1)
        value = ai_output.get(field)
        if value is None:
            return ""
        return str(value)

    return re.sub(r"\{(\w+)\}", replacer, template)


async def execute(
    config: dict[str, Any],
    ai_output: dict[str, Any],
    access_token: str,
    run_step_id: str | None = None,
) -> dict[str, Any]:
    """
    Post a message to Slack using the chat.postMessage API.
    Handles 429 rate limits with Retry-After backoff.
    Returns {ok, ts, channel}.
    """
    channel = config.get("channel", "")
    template = config.get("template", "")

    if not channel:
        raise ValueError("Slack action config missing 'channel'")
    if not template:
        raise ValueError("Slack action config missing 'template'")

    text = _render_template(template, ai_output)

    payload = {
        "channel": channel,
        "text": text,
    }

    for attempt in range(3):
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                SLACK_POST_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 2 ** (attempt + 1)))
                await asyncio.sleep(retry_after)
                continue

            resp.raise_for_status()
            data = resp.json()

        if not data.get("ok"):
            error = data.get("error", "unknown")
            if error == "rate_limited":
                await asyncio.sleep(2 ** attempt)
                continue
            raise ValueError(f"Slack postMessage failed: {error}")

        return {
            "ok": True,
            "ts": data.get("ts"),
            "channel": data.get("channel"),
            "rendered_text": text,
        }

    raise ValueError("Slack postMessage failed after 3 attempts (rate limited)")