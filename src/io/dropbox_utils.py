# src/io/dropbox_utils.py

"""
Archivist I/O: Dropbox Authentication Logic.

Compliance:
- Rule 0 (Law of Performance): Uses __slots__ to eliminate memory overhead.
- Rule 5 (Deterministic Init): Requires explicit config instantiation.
- Rule 8 (API Minimalism): Unified interface for token management.
"""

from typing import Final

import requests


class TokenManager:
    """
    Manages OAuth2 token lifecycle with strict memory management.
    """
    __slots__ = ['_client_id', '_client_secret']
    
    TOKEN_URL: Final = "https://api.dropbox.com/oauth2/token"

    def __init__(self, client_id: str, client_secret: str):
        # Rule 5: Deterministic Initialization
        self._client_id = client_id
        self._client_secret = client_secret

    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Refreshes the OAuth2 access token.
        """
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self._client_id,
            "client_secret": self._client_secret
        }
        
        response = requests.post(self.TOKEN_URL, data=payload)
        
        if response.status_code == 200:
            return response.json()["access_token"]
        
        # Explicit error reporting for CI/CD logs
        raise RuntimeError(
            f"❌ Dropbox Auth Failed | Status: {response.status_code} | Body: {response.text}"
        )