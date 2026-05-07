from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.integrations.base import BaseOAuthProvider

SCOPES = " ".join([
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
])
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
PROFILE_URL = "https://gmail.googleapis.com/gmail/v1/users/me/profile"


class GmailOAuthProvider(BaseOAuthProvider):
    """Handles Gmail OAuth 2.0 flow with offline access and token refresh."""

    def get_auth_url(self, state: str) -> str:
        """Build the Google OAuth authorization URL."""
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": SCOPES,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        """Exchange auth code for access + refresh tokens."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        if "error" in data:
            raise ValueError(f"Gmail token exchange failed: {data['error']}")

        return data

    async def get_account_info(self, access_token: str) -> dict:
        """Get Gmail profile to use as account identifier."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                PROFILE_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "account_id": data["emailAddress"],
            "display_name": data["emailAddress"],
            "history_id": data.get("historyId"),
        }

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """
        Exchange a refresh token for a new access token.
        Returns {access_token, expires_in}.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                TOKEN_URL,
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        if "error" in data:
            raise ValueError(f"Gmail token refresh failed: {data['error']}")

        return data