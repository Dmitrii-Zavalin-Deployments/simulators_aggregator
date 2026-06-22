# tests/io/download_from_dropbox/test_positive.py

from pathlib import Path
import pytest
import os
from unittest.mock import patch, MagicMock
from src.io.dropbox_utils import TokenManager
from src.io.download_from_dropbox import CloudIngestor

# Rule 5: Operational Hygiene - Verifying Deterministic Sync Logic

class TestCloudIngestor:
    """
    Validation Suite for Infrastructure I/O.
    Ensures the 'Foundation' (Dropbox) can be reached deterministically.
    """

    @pytest.fixture
    def mock_env(self):
        """Rule 4: Zero-Default Policy - Testing against explicit environment keys."""
        with patch.dict(os.environ, {
            "APP_KEY": "test_key",
            "APP_SECRET": "test_secret",
            "REFRESH_TOKEN": "test_refresh"
        }):
            yield

    def test_token_refresh_logic(self, mock_env):
        """
        Rule 5 (Nomadic Sustainability): Handles token expiration automatically.
        """
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"access_token": "new_temp_token"}
            
            # Implementation Fix: Use TokenManager with required credentials
            client = TokenManager(os.environ['APP_KEY'], os.environ['APP_SECRET'])
            token = client.refresh_access_token("some_refresh_token")
            
            assert token == "new_temp_token"
            mock_post.assert_called_once()
            print("\n✅ Token Refresh Logic: Deterministic")

    @patch("dropbox.Dropbox")
    def test_pagination_continuity(self, mock_dbx_class, mock_env):
        """
        Rule 1: Isolation Mandate - Ensures full artifact sync across pages.
        """
        mock_dbx = mock_dbx_class.return_value
        
        # Mocking the actual Dropbox SDK return values (pagination logic)
        page1 = MagicMock()
        page1.entries = [MagicMock(name="file1.json", path_lower="/test/file1.json")]
        page1.has_more = True
        page1.cursor = "c1"
        
        page2 = MagicMock()
        page2.entries = [MagicMock(name="file2.json", path_lower="/test/file2.json")]
        page2.has_more = False
        
        mock_dbx.files_list_folder.return_value = page1
        mock_dbx.files_list_folder_continue.return_value = page2

        # Ingestor uses TokenManager + CloudIngestor
        with patch("requests.post") as m:
            m.return_value.status_code = 200
            m.return_value.json.return_value = {"access_token": "mock"}
            tm = TokenManager("key", "secret")
            ingestor = CloudIngestor(tm, "refresh", "test.log")
        
        # This triggers the internal pagination loop in CloudIngestor
        with patch("builtins.open", MagicMock()), patch("pathlib.Path.mkdir"):
            ingestor.sync("/test", Path("./local"), [".json"])
            
        assert mock_dbx.files_list_folder.called
        assert mock_dbx.files_list_folder_continue.called
        print("\n✅ Pagination Logic: Deterministic")

    def test_hard_halt_on_auth_failure(self, mock_env):
        """
        Rule 4: Zero-Default Policy - Engine must crash on invalid credentials.
        """
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 401
            mock_post.return_value.text = "Dropbox Auth Failed"
            
            client = TokenManager("key", "secret")
            with pytest.raises(RuntimeError, match="Dropbox Auth Failed"):
                client.refresh_access_token("bad_token")
            
            print("\n✅ Auth Failure: Hard-Halt Confirmed")