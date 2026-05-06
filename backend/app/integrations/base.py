from abc import ABC, abstractmethod


class BaseOAuthProvider(ABC):
    """Abstract base for all OAuth integration providers."""

    @abstractmethod
    def get_auth_url(self, state: str) -> str:
        """Return the full authorization URL to redirect the user to."""
        ...

    @abstractmethod
    async def exchange_code(self, code: str) -> dict:
        """Exchange auth code for tokens. Returns raw token response dict."""
        ...

    @abstractmethod
    async def get_account_info(self, access_token: str) -> dict:
        """Return platform account info: {account_id, display_name}."""
        ...