import base64
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.integrations.base import BaseOAuthProvider

SCOPES = "chat:write,chat:write.public,channels:read,users:read"
AUTH_URL = "https://slack.com/oauth/v2/authorize"
TOKEN_URL = "https://slack.com/api/oauth.v2.access"
AUTH_TEST_URL = "https://slack.com/api/auth.test"


class SlackOAuthProvider(BaseOAuthProvider):
    """Handles Slack OAuth 2.0 flow."""

    def get_auth_url(self, state: str) -> str:
        """Build the Slack OAuth authorization URL."""
        params = {
            "client_id": settings.slack_client_id,
            "scope": SCOPES,
            "redirect_uri": settings.slack_redirect_uri,
            "state": state,
        }
        return f"{AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        """
        Exchange the auth code for a bot token.
        Uses HTTP Basic auth with client_id:client_secret.
        """
        credentials = base64.b64encode(
            f"{settings.slack_client_id}:{settings.slack_client_secret}".encode()
        ).decode()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                TOKEN_URL,
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "code": code,
                    "redirect_uri": settings.slack_redirect_uri,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        if not data.get("ok"):
            raise ValueError(f"Slack token exchange failed: {data.get('error', 'unknown')}")

        return data

    async def get_account_info(self, access_token: str) -> dict:
        """
        Call Slack auth.test to verify token and get workspace info.
        Returns {account_id, display_name}.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                AUTH_TEST_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()

        if not data.get("ok"):
            raise ValueError(f"Slack auth.test failed: {data.get('error', 'unknown')}")

        return {
            "account_id": data["team_id"],
            "display_name": data["team"],
        }