import json
import re
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system import PromptTemplate
from app.services.llm_client import call_openai


def _build_schema_description(output_schema: dict[str, Any]) -> str:
    """Convert output_schema dict to a human-readable description for the prompt."""
    lines = []
    for field_name, spec in output_schema.items():
        field_type = spec.get("type", "string")
        enum_values = spec.get("enum")
        description = spec.get("description", "")

        line = f"- {field_name} ({field_type})"
        if enum_values:
            line += f": one of {enum_values}"
        if description:
            line += f" — {description}"
        lines.append(line)
    return "\n".join(lines)


def _extract_json(content: str) -> dict:
    """
    Extract a JSON object from LLM response content.
    Handles responses wrapped in markdown code blocks.
    Raises ValueError if no valid JSON found.
    """
    # Strip markdown code blocks
    content = re.sub(r"```(?:json)?\s*", "", content).strip()
    content = content.rstrip("`").strip()

    # Try direct parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object within text
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No valid JSON found in LLM response: {content[:200]}")


def _validate_output(parsed: dict, output_schema: dict[str, Any]) -> dict:
    """
    Validate that parsed output contains all required fields
    and that enum fields have valid values.
    Raises ValueError with details on failure.
    """
    errors = []

    for field_name, spec in output_schema.items():
        if field_name not in parsed:
            errors.append(f"Missing required field: '{field_name}'")
            continue

        value = parsed[field_name]
        field_type = spec.get("type", "string")
        enum_values = spec.get("enum")

        # Type check
        type_map = {"string": str, "integer": int, "boolean": bool, "array": list}
        expected_type = type_map.get(field_type, str)
        if not isinstance(value, expected_type):
            errors.append(
                f"Field '{field_name}' expected {field_type}, got {type(value).__name__}"
            )

        # Enum check
        if enum_values and value not in enum_values:
            errors.append(
                f"Field '{field_name}' value '{value}' not in allowed values: {enum_values}"
            )

    if errors:
        raise ValueError(f"Output validation failed: {'; '.join(errors)}")

    return parsed


async def process_ai_step(
    db: AsyncSession,
    task_type: str,
    input_text: str,
    output_schema: dict[str, Any],
    model: str = "gpt-4o-mini",
    few_shot_examples: list | None = None,
) -> dict[str, Any]:
    """
    Full AI step processor with corrective retry loop.

    Flow:
    1. Load active prompt template for task_type
    2. Build messages with input + schema
    3. Call LLM
    4. Parse JSON from response
    5. Validate against output_schema
    6. If validation fails: inject error into prompt and retry (max 3 attempts)
    7. Return {output: dict, prompt_tokens, completion_tokens, cost_usd, model, attempts}
    """
    # Load prompt template
    result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.task_type == task_type,
            PromptTemplate.is_active == True,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise ValueError(f"No active prompt template found for task_type: {task_type}")

    schema_description = _build_schema_description(output_schema)

    user_content = template.user_prompt_template.format(
        input_text=input_text,
        output_schema=schema_description,
    )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": template.system_prompt},
    ]

    # Add few-shot examples if provided
    if few_shot_examples:
        for example in few_shot_examples:
            messages.append({"role": "user", "content": example.get("input", "")})
            messages.append({"role": "assistant", "content": json.dumps(example.get("output", {}))})

    messages.append({"role": "user", "content": user_content})

    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_cost_usd = 0.0
    last_error: str | None = None

    for attempt in range(1, 4):  # Max 3 attempts
        llm_result = await call_openai(messages=messages, model=model)

        total_prompt_tokens += llm_result["prompt_tokens"]
        total_completion_tokens += llm_result["completion_tokens"]
        total_cost_usd += llm_result["cost_usd"]

        try:
            parsed = _extract_json(llm_result["content"])
            validated = _validate_output(parsed, output_schema)

            return {
                "output": validated,
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "cost_usd": total_cost_usd,
                "model": model,
                "attempts": attempt,
                "raw_response": llm_result["content"],
            }

        except ValueError as e:
            last_error = str(e)

            # Corrective retry: append error and ask LLM to fix
            messages.append({"role": "assistant", "content": llm_result["content"]})
            messages.append({
                "role": "user",
                "content": (
                    f"Your response failed validation with this error:\n{last_error}\n\n"
                    f"Please correct your response. Return ONLY a valid JSON object "
                    f"matching the schema. No markdown, no explanation."
                ),
            })

    raise ValueError(
        f"AI step failed after 3 attempts. Last error: {last_error}"
    )