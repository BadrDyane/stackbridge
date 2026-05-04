from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Database
    database_url: str
    database_url_sync: str

    # Application
    app_secret_key: str
    environment: str = "development"
    cors_origins: str = "http://localhost:5173"
    jwt_expiry_minutes: int = 60
    jwt_refresh_expiry_days: int = 30
    encryption_key: str

    # OpenAI
    openai_api_key: str
    openai_default_model: str = "gpt-4o-mini"
    openai_api_base_url: str = "https://api.openai.com/v1"

    # Google / Gmail
    google_client_id: str = "placeholder"
    google_client_secret: str = "placeholder"
    google_redirect_uri: str = "http://localhost:8000/integrations/gmail/callback"

    # Slack
    slack_client_id: str = "placeholder"
    slack_client_secret: str = "placeholder"
    slack_redirect_uri: str = "http://localhost:8000/integrations/slack/callback"
    slack_signing_secret: str = "placeholder"

    # Notion
    notion_client_id: str = "placeholder"
    notion_client_secret: str = "placeholder"
    notion_redirect_uri: str = "http://localhost:8000/integrations/notion/callback"

    # Scheduler
    scheduler_jobstore_url: str = "sqlite:///./scheduler_jobs.db"
    gmail_polling_default_interval_seconds: int = 300
    idempotency_key_ttl_days: int = 7

    # Feature flags
    enable_dry_run: bool = True
    max_ai_retries: int = 3
    max_action_retries: int = 3

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()