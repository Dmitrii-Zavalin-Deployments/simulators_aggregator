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

# The TokenManager encapsulates the OAuth2 handshake.
# We utilize __slots__ to enforce fixed memory allocation, preventing
# the creation of instance __dict__ attributes, which satisfies Rule 0.
class TokenManager:
    """
    Manages OAuth2 token lifecycle with strict memory management.
    """
    __slots__ = ['_client_id', '_client_secret']
    
    # We define the constant endpoint for the token exchange as per Dropbox API documentation.
    TOKEN_URL: Final = "https://api.dropbox.com/oauth2/token"

    # Deterministic initialization ensures that the TokenManager is not 
    # reliant on implicit global state or hidden environment access during instantiation.
    def __init__(self, client_id: str, client_secret: str):
        self._client_id = client_id
        self._client_secret = client_secret

    # The token refresh process is the core mechanism of the session lifecycle.
    # It requires a POST request containing the refresh token and application credentials.
    def refresh_access_token(self, refresh_token: str) -> str:
        
        # We construct the payload following the RFC 6749 standard for OAuth2:
        #     grant_type = 'refresh_token'
        #     client_id  = self._client_id
        #     ...
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self._client_id,
            "client_secret": self._client_secret
        }
        
        # We execute the network call to the Dropbox token endpoint.
        response = requests.post(self.TOKEN_URL, data=payload)
        
        # The system enforces strict error checking. If the status code is not 200 OK,
        # we raise a RuntimeError to prevent the system from continuing with 
        # invalid authentication credentials.
        if response.status_code == 200:
            # On success, we parse the JSON response to extract the new token.
            return response.json()["access_token"]
        
        # Failure reporting: We expose the response text for auditing in CI/CD logs.
        raise RuntimeError(
            f"❌ Dropbox Auth Failed | Status: {response.status_code} | Body: {response.text}"
        )