import secrets
import time
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_token, encrypt_token
from app.integrations.slack.oauth import SlackOAuthProvider
from app.models.integration import Integration

# In-memory OAuth state store: {state: {user_id, platform, expires_at (float)}}
_oauth_states: dict[str, dict] = {}

# Registry of OAuth providers
_PROVIDERS = {
    "slack": SlackOAuthProvider(),
}


def _clean_expired_states() -> None:
    """Remove expired OAuth states from memory."""
    now = time.time()
    expired = [k for k, v in _oauth_states.items() if v["expires_at"] < now]
    for k in expired:
        del _oauth_states[k]


def start_oauth(platform: str, user_id: uuid.UUID) -> str:
    """
    Generate an OAuth state token and return the provider's authorization URL.
    State expires in 10 minutes.
    """
    if platform not in _PROVIDERS:
        raise ValueError(f"Unsupported platform: {platform}")

    _clean_expired_states()

    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "user_id": str(user_id),
        "platform": platform,
        "expires_at": time.time() + 600,  # 10 minutes
    }

    provider = _PROVIDERS[platform]
    return provider.get_auth_url(state)


async def handle_callback(
    platform: str,
    code: str,
    state: str,
    db: AsyncSession,
) -> Integration:
    """
    Validate OAuth state, exchange code for token, encrypt and store.
    Returns the created Integration ORM object.
    """
    _clean_expired_states()

    state_data = _oauth_states.get(state)
    if not state_data:
        raise ValueError("Invalid or expired OAuth state — please try connecting again")
    if time.time() > state_data["expires_at"]:
        del _oauth_states[state]
        raise ValueError("OAuth state has expired — please try connecting again")

    user_id = uuid.UUID(state_data["user_id"])
    del _oauth_states[state]  # State is single-use

    if platform not in _PROVIDERS:
        raise ValueError(f"Unsupported platform: {platform}")

    provider = _PROVIDERS[platform]

    # Exchange code for token
    token_data = await provider.exchange_code(code)

    # Extract access token (platform-specific)
    if platform == "slack":
        access_token = token_data["access_token"]
        refresh_token = None
        token_expires_at = None
        scopes = token_data.get("scope", "").split(",")
    else:
        raise ValueError(f"handle_callback not implemented for platform: {platform}")

    # Get account info for display name and dedup check
    account_info = await provider.get_account_info(access_token)
    account_id = account_info["account_id"]
    display_name = account_info["display_name"]

    # Check for existing active integration for this workspace
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
        existing.display_name = display_name
        await db.commit()
        await db.refresh(existing)
        return existing

    # Create new integration
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
    )
    db.add(integration)
    await db.commit()
    await db.refresh(integration)
    return integration


async def get_valid_token(integration_id: uuid.UUID, db: AsyncSession) -> str:
    """Retrieve and decrypt the access token for an integration."""
    result = await db.execute(
        select(Integration).where(
            Integration.id == integration_id,
            Integration.is_active == True,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise ValueError(f"Integration {integration_id} not found or inactive")

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
    """Soft-delete an integration by marking it inactive."""
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
    """Verify the integration token is still valid."""
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

    access_token = decrypt_token(integration.access_token)

    if integration.platform == "slack":
        provider = SlackOAuthProvider()
        info = await provider.get_account_info(access_token)
        return {"ok": True, "platform": "slack", "team": info["display_name"]}
    else:
        raise ValueError(f"Test not implemented for platform: {integration.platform}")