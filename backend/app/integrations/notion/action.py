import re
from typing import Any

import httpx

NOTION_PAGES_URL = "https://api.notion.com/v1/pages"
NOTION_VERSION = "2022-06-28"


def _render_template(template: str, ai_output: dict[str, Any]) -> str:
    """Replace {field_name} placeholders with values from ai_output."""
    def replacer(match: re.Match) -> str:
        field = match.group(1)
        value = ai_output.get(field)
        if value is None:
            return ""
        return str(value)

    return re.sub(r"\{(\w+)\}", replacer, template)


def _build_rich_text(text: str) -> list[dict]:
    """Convert a plain text string to Notion rich_text format."""
    return [{"type": "text", "text": {"content": text[:2000]}}]


async def execute(
    config: dict[str, Any],
    ai_output: dict[str, Any],
    access_token: str,
    run_step_id: str | None = None,
) -> dict[str, Any]:
    """
    Create a Notion page with AI-generated content.
    Uses Idempotency-Key header to prevent duplicate pages on retry.
    Returns {id, url}.
    """
    parent_page_id = config.get("parent_page_id", "")
    title_template = config.get("title_template", "New Entry")
    body_template = config.get("body_template", "")

    if not parent_page_id:
        raise ValueError("Notion action config missing 'parent_page_id'")

    title = _render_template(title_template, ai_output)
    body = _render_template(body_template, ai_output)

    page_payload = {
        "parent": {"page_id": parent_page_id},
        "properties": {
            "title": {
                "title": _build_rich_text(title)
            }
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": _build_rich_text(body)
                },
            }
        ] if body else [],
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }
    if run_step_id:
        headers["Idempotency-Key"] = str(run_step_id)

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(NOTION_PAGES_URL, headers=headers, json=page_payload)
        resp.raise_for_status()
        data = resp.json()

    return {
        "ok": True,
        "id": data.get("id"),
        "url": data.get("url"),
        "title": title,
    }