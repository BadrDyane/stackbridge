import base64
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.integrations.base import BaseOAuthProvider

AUTH_URL = "https://api.notion.com/v1/oauth/authorize"
TOKEN_URL = "https://api.notion.com/v1/oauth/token"


class NotionOAuthProvider(BaseOAuthProvider):
    """Handles Notion OAuth 2.0 flow. Tokens do not expire."""

    def get_auth_url(self, state: str) -> str:
        """Build the Notion OAuth authorization URL."""
        params = {
            "client_id": settings.notion_client_id,
            "redirect_uri": settings.notion_redirect_uri,
            "response_type": "code",
            "owner": "user",
            "state": state,
        }
        return f"{AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        """Exchange auth code for a permanent access token."""
        credentials = base64.b64encode(
            f"{settings.notion_client_id}:{settings.notion_client_secret}".encode()
        ).decode()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                TOKEN_URL,
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/json",
                },
                json={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.notion_redirect_uri,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        if "error" in data:
            raise ValueError(f"Notion token exchange failed: {data['error']}")

        return data

    async def get_account_info(self, access_token: str) -> dict:
        """Get Notion workspace info."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.notion.com/v1/users/me",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Notion-Version": "2022-06-28",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "account_id": data.get("id", "unknown"),
            "display_name": data.get("name", "Notion Workspace"),
        }