import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.integration import AuthUrlResponse, IntegrationResponse
from app.services import integration_service

router = APIRouter(prefix="/integrations", tags=["integrations"])

SUPPORTED_PLATFORMS = ["slack"]


@router.get("/{platform}/auth-url", response_model=AuthUrlResponse)
async def get_auth_url(
    platform: str,
    current_user: User = Depends(get_current_user),
) -> AuthUrlResponse:
    """Generate the OAuth authorization URL for the given platform."""
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform: {platform}. Supported: {SUPPORTED_PLATFORMS}",
        )
    try:
        auth_url = integration_service.start_oauth(platform, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return AuthUrlResponse(auth_url=auth_url, platform=platform)


@router.get("/{platform}/callback")
async def oauth_callback(
    platform: str,
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle the OAuth callback from the provider.
    No auth dependency — the state token proves identity.
    Redirects browser to frontend on success.
    """
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform: {platform}",
        )
    try:
        integration = await integration_service.handle_callback(platform, code, state, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Redirect to frontend integrations page after successful connection
    return RedirectResponse(url="http://localhost:5173/integrations?connected=slack")


@router.get("", response_model=list[IntegrationResponse])
async def list_integrations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[IntegrationResponse]:
    """List all active integrations for the current user."""
    return await integration_service.list_integrations(current_user.id, db)


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(
    integration_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Disconnect (soft-delete) an integration."""
    try:
        await integration_service.delete_integration(integration_id, current_user.id, db)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")


@router.post("/{integration_id}/test")
async def test_integration(
    integration_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Verify an integration's token is still valid."""
    try:
        return await integration_service.test_integration(integration_id, current_user.id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))