import asyncio
from typing import Any

import httpx

from app.core.config import settings

OPENAI_CHAT_URL = f"{settings.openai_api_base_url}/chat/completions"

# Cost per 1M tokens in USD (gpt-4o-mini)
MODEL_COSTS: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"prompt": 0.15, "completion": 0.60},
    "gpt-4o": {"prompt": 2.50, "completion": 10.00},
}


async def call_openai(
    messages: list[dict[str, str]],
    model: str = "gpt-4o-mini",
    max_tokens: int = 1000,
    response_format: dict | None = None,
) -> dict[str, Any]:
    """
    Call OpenAI chat completions via direct REST (no SDK).
    Returns {content, prompt_tokens, completion_tokens, cost_usd}.
    Retries up to 3 times on 429 with exponential backoff.
    """
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if response_format:
        body["response_format"] = response_format

    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    last_error: Exception | None = None

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(OPENAI_CHAT_URL, json=body, headers=headers)

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 2 ** (attempt + 1)))
                    await asyncio.sleep(retry_after)
                    last_error = ValueError(f"OpenAI rate limited (attempt {attempt + 1})")
                    continue

                resp.raise_for_status()
                data = resp.json()

        except httpx.HTTPStatusError as e:
            last_error = e
            await asyncio.sleep(2 ** attempt)
            continue

        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        costs = MODEL_COSTS.get(model, MODEL_COSTS["gpt-4o-mini"])
        cost_usd = (
            (prompt_tokens / 1_000_000) * costs["prompt"]
            + (completion_tokens / 1_000_000) * costs["completion"]
        )

        content = data["choices"][0]["message"]["content"]

        return {
            "content": content,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost_usd,
            "model": model,
        }

    raise ValueError(f"OpenAI call failed after 3 attempts: {last_error}")