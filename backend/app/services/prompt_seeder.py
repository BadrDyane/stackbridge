from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.system import PromptTemplate

TEMPLATES = [
    {
        "task_type": "classify_and_summarize",
        "version": 1,
        "is_active": True,
        "system_prompt": (
            "You are an intelligent workflow assistant. "
            "Analyze the input and produce a JSON object that exactly matches the output schema provided. "
            "Return ONLY valid JSON. No markdown, no explanation, no code blocks."
        ),
        "user_prompt_template": (
            "Analyze the following input and classify/summarize it.\n\n"
            "Input:\n{input_text}\n\n"
            "Output schema (produce JSON matching these fields exactly):\n{output_schema}\n\n"
            "Return only a valid JSON object."
        ),
        "few_shot_examples": None,
    },
    {
        "task_type": "extract_fields",
        "version": 1,
        "is_active": True,
        "system_prompt": (
            "You are a precise data extraction assistant. "
            "Extract the requested fields from the input and return a JSON object. "
            "Return ONLY valid JSON. No markdown, no explanation, no code blocks."
        ),
        "user_prompt_template": (
            "Extract the following fields from the input.\n\n"
            "Input:\n{input_text}\n\n"
            "Fields to extract (return JSON matching these fields):\n{output_schema}\n\n"
            "Return only a valid JSON object."
        ),
        "few_shot_examples": None,
    },
    {
        "task_type": "generate_content",
        "version": 1,
        "is_active": True,
        "system_prompt": (
            "You are a content generation assistant. "
            "Generate content based on the input and schema provided. "
            "Return ONLY valid JSON. No markdown, no explanation, no code blocks."
        ),
        "user_prompt_template": (
            "Generate content based on the following input.\n\n"
            "Input:\n{input_text}\n\n"
            "Output schema:\n{output_schema}\n\n"
            "Return only a valid JSON object."
        ),
        "few_shot_examples": None,
    },
]


async def seed_prompt_templates() -> None:
    """Insert default prompt templates if they don't already exist."""
    async with AsyncSessionLocal() as db:
        for template_data in TEMPLATES:
            result = await db.execute(
                select(PromptTemplate).where(
                    PromptTemplate.task_type == template_data["task_type"],
                    PromptTemplate.is_active == True,
                )
            )
            if result.scalar_one_or_none():
                continue  # Already seeded

            template = PromptTemplate(**template_data)
            db.add(template)

        await db.commit()