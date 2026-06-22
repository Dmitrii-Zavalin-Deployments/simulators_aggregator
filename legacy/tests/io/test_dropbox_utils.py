# tests/io/test_dropbox_utils.py

import pytest
import requests
from unittest.mock import patch, MagicMock
from src.io.dropbox_utils import TokenManager

class TestTokenManager:
    @pytest.fixture
    def token_manager(self):
        """Rule 5: Deterministic Initialization for testing."""
        return TokenManager(client_id="mock_id", client_secret="mock_secret")

    # --- SECTION 1: SUCCESS PATH ---

    def test_refresh_access_token_success(self, token_manager):
        """Verifies the 200 OK path and JSON extraction."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "new_secret_token"}
        
        with patch("requests.post", return_value=mock_response):
            token = token_manager.refresh_access_token("refresh_val")
            assert token == "new_secret_token"

    # --- SECTION 2: LOGIC FAILURES ---

    def test_refresh_access_token_auth_failure(self, token_manager):
        """Verifies the 401/400 path (Lines 54-57)."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid Grant"
        
        with patch("requests.post", return_value=mock_response):
            with pytest.raises(RuntimeError, match="Dropbox Auth Failed"):
                token_manager.refresh_access_token("bad_refresh_val")

    # --- SECTION 3: NETWORK ERRORS (THE 100% COVERAGE GAP) ---

    def test_refresh_access_token_network_error(self, token_manager):
        """
        Covers Lines 59-61: Simulates a network-level exception.
        This forces the code into the critical logger and re-raises the error.
        """
        # We simulate a connection timeout/error from the requests library
        with patch("requests.post", side_effect=requests.exceptions.RequestException("DNS Timeout")):
            with pytest.raises(requests.exceptions.RequestException, match="DNS Timeout"):
                token_manager.refresh_access_token("any_token")
                
    def test_slots_compliance(self, token_manager):
        """Rule 0: Verify __slots__ is effectively preventing dynamic dicts."""
        with pytest.raises(AttributeError):
            token_manager.new_attr = "this should fail"