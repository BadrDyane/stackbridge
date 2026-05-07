import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_token, encrypt_token
from app.integrations.gmail.oauth import GmailOAuthProvider
from app.integrations.notion.oauth import NotionOAuthProvider
from app.integrations.slack.oauth import SlackOAuthProvider
from app.models.integration import Integration

# In-memory OAuth state store: {state: {user_id, platform, expires_at (float)}}
_oauth_states: dict[str, dict] = {}

_PROVIDERS = {
    "slack": SlackOAuthProvider(),
    "gmail": GmailOAuthProvider(),
    "notion": NotionOAuthProvider(),
}

SUPPORTED_PLATFORMS = list(_PROVIDERS.keys())


def _clean_expired_states() -> None:
    """Remove expired OAuth states from memory."""
    now = time.time()
    expired = [k for k, v in _oauth_states.items() if v["expires_at"] < now]
    for k in expired:
        del _oauth_states[k]


def start_oauth(platform: str, user_id: uuid.UUID) -> str:
    """Generate an OAuth state token and return the provider's authorization URL."""
    if platform not in _PROVIDERS:
        raise ValueError(f"Unsupported platform: {platform}")

    _clean_expired_states()

    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "user_id": str(user_id),
        "platform": platform,
        "expires_at": time.time() + 600,
    }

    return _PROVIDERS[platform].get_auth_url(state)


async def handle_callback(
    platform: str,
    code: str,
    state: str,
    db: AsyncSession,
) -> Integration:
    """Validate OAuth state, exchange code for token, encrypt and store."""
    _clean_expired_states()

    state_data = _oauth_states.get(state)
    if not state_data:
        raise ValueError("Invalid or expired OAuth state — please try connecting again")
    if time.time() > state_data["expires_at"]:
        del _oauth_states[state]
        raise ValueError("OAuth state has expired — please try connecting again")

    user_id = uuid.UUID(state_data["user_id"])
    del _oauth_states[state]

    if platform not in _PROVIDERS:
        raise ValueError(f"Unsupported platform: {platform}")

    provider = _PROVIDERS[platform]
    token_data = await provider.exchange_code(code)

    # Extract tokens per platform
    if platform == "slack":
        access_token = token_data["access_token"]
        refresh_token = None
        token_expires_at = None
        scopes = token_data.get("scope", "").split(",")
        extra_metadata = {"bot_user_id": token_data.get("bot_user_id")}

    elif platform == "gmail":
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)
        token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        scopes = token_data.get("scope", "").split(" ")
        extra_metadata = {}

    elif platform == "notion":
        access_token = token_data["access_token"]
        refresh_token = None
        token_expires_at = None
        scopes = []
        extra_metadata = {
            "workspace_id": token_data.get("workspace_id"),
            "workspace_name": token_data.get("workspace_name"),
        }

    else:
        raise ValueError(f"handle_callback not implemented for: {platform}")

    account_info = await provider.get_account_info(access_token)
    account_id = account_info["account_id"]
    display_name = account_info["display_name"]

    # Store initial Gmail historyId in extra_metadata for polling seed
    if platform == "gmail" and "history_id" in account_info:
        extra_metadata["initial_history_id"] = account_info["history_id"]

    # Check for existing active integration
    result = await db.execute(
        select(Integration).where(
            Integration.user_id == user_id,
            Integration.platform == platform,
            Integration.platform_account_id == account_id,
            Integration.is_active == True,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.access_token = encrypt_token(access_token)
        if refresh_token:
            existing.refresh_token = encrypt_token(refresh_token)
        existing.token_expires_at = token_expires_at
        existing.display_name = display_name
        existing.extra_metadata = extra_metadata
        await db.commit()
        await db.refresh(existing)
        return existing

    integration = Integration(
        user_id=user_id,
        platform=platform,
        display_name=display_name,
        access_token=encrypt_token(access_token),
        refresh_token=encrypt_token(refresh_token) if refresh_token else None,
        token_expires_at=token_expires_at,
        scopes=scopes,
        platform_account_id=account_id,
        is_active=True,
        extra_metadata=extra_metadata,
    )
    db.add(integration)
    await db.commit()
    await db.refresh(integration)
    return integration


async def get_valid_token(integration_id: uuid.UUID, db: AsyncSession) -> str:
    """
    Retrieve and decrypt the access token.
    For Gmail: refreshes if expired.
    """
    result = await db.execute(
        select(Integration).where(
            Integration.id == integration_id,
            Integration.is_active == True,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise ValueError(f"Integration {integration_id} not found or inactive")

    # Refresh Gmail token if expired
    if integration.platform == "gmail" and integration.token_expires_at:
        now = datetime.now(timezone.utc)
        expires_at = integration.token_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now >= expires_at - timedelta(minutes=5):
            if not integration.refresh_token:
                integration.is_active = False
                await db.commit()
                raise ValueError("Gmail token expired and no refresh token available")
            provider = GmailOAuthProvider()
            refresh_token = decrypt_token(integration.refresh_token)
            try:
                new_token_data = await provider.refresh_access_token(refresh_token)
            except Exception:
                integration.is_active = False
                await db.commit()
                raise ValueError("Gmail token refresh failed — user must reconnect")
            integration.access_token = encrypt_token(new_token_data["access_token"])
            integration.token_expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=new_token_data.get("expires_in", 3600)
            )
            await db.commit()

    return decrypt_token(integration.access_token)


async def list_integrations(user_id: uuid.UUID, db: AsyncSession) -> list[Integration]:
    """Return all active integrations for the user."""
    result = await db.execute(
        select(Integration)
        .where(Integration.user_id == user_id, Integration.is_active == True)
        .order_by(Integration.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_integration(
    integration_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """Soft-delete an integration."""
    result = await db.execute(
        select(Integration).where(
            Integration.id == integration_id,
            Integration.user_id == user_id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise ValueError("Integration not found")
    integration.is_active = False
    await db.commit()


async def test_integration(
    integration_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> dict:
    """Verify an integration token is still valid."""
    result = await db.execute(
        select(Integration).where(
            Integration.id == integration_id,
            Integration.user_id == user_id,
            Integration.is_active == True,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise ValueError("Integration not found")

    access_token = await get_valid_token(integration_id, db)

    if integration.platform == "slack":
        provider = SlackOAuthProvider()
        info = await provider.get_account_info(access_token)
        return {"ok": True, "platform": "slack", "team": info["display_name"]}

    elif integration.platform == "gmail":
        provider = GmailOAuthProvider()
        info = await provider.get_account_info(access_token)
        return {"ok": True, "platform": "gmail", "email": info["display_name"]}

    elif integration.platform == "notion":
        provider = NotionOAuthProvider()
        info = await provider.get_account_info(access_token)
        return {"ok": True, "platform": "notion", "workspace": info["display_name"]}

    else:
        raise ValueError(f"Test not implemented for: {integration.platform}")