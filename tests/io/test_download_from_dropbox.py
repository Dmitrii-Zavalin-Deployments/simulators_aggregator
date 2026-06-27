"""
Archivist I/O: Test Suite
-------------------------------------------------------------------------------
This suite validates the Cloud Ingestion Module against the Project Constitution
Protocol. It covers environment enforcement, deterministic authentication,
and atomic file operations.
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch
import dropbox

from src.io.download_from_dropbox import CloudIngestor, _get_required_env
from src.io.dropbox_utils import TokenManager

# =============================================================================
# 1. Enforcement of No-Default Policy
# =============================================================================

# The Environment Helper must enforce explicit configuration. 
# If a key is missing, the system must halt immediately (Rule 0 / No-Default Policy).

def test_get_required_env_success(monkeypatch):
    """Verify that valid environment variables are returned cleanly."""
    monkeypatch.setenv("TEST_KEY", "value")
    assert _get_required_env("TEST_KEY") == "value"

def test_get_required_env_missing():
    """Verify that missing environment variables trigger an EnvironmentError."""
    with pytest.raises(EnvironmentError):
        _get_required_env("NON_EXISTENT_KEY")


# =============================================================================
# 2. Deterministic Authentication (Rule 5)
# =============================================================================

# TokenManager provides the gateway to the cloud. We verify that tokens are
# refreshed deterministically using the provided credentials.

def test_token_manager_refresh_success():
    """Verify that the TokenManager correctly executes a POST request to refresh tokens."""
    tm = TokenManager(client_id="fake_id", client_secret="fake_secret")
    
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"access_token": "new_shiny_token"}
        
        token = tm.refresh_access_token("refresh_me")
        assert token == "new_shiny_token"
        
        # Verify payload contains exact expected credentials
        _, kwargs = mock_post.call_args
        assert kwargs['data']['client_id'] == "fake_id"
        assert kwargs['data']['client_secret'] == "fake_secret"

def test_token_manager_refresh_failure():
    """Verify that unauthorized requests raise a RuntimeError per the No-Default Policy."""
    tm = TokenManager(client_id="fake_id", client_secret="fake_secret")
    
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 401
        mock_post.return_value.text = "Unauthorized"
        
        with pytest.raises(RuntimeError, match="Dropbox Auth Failed"):
            tm.refresh_access_token("bad_token")


# =============================================================================
# 3. CloudIngestor Operational Logic (Rule 8)
# =============================================================================

# The CloudIngestor acts as an atomic synchronization agent. We use dependency 
# injection for the Dropbox client to ensure tests do not rely on actual network state.

@pytest.fixture
def mock_ingestor(tmp_path):
    """Fixture to provide a fully initialized CloudIngestor with mocked dependencies."""
    mock_tm = MagicMock(spec=TokenManager)
    mock_tm.refresh_access_token.return_value = "fake_token"
    log_path = tmp_path / "download.log"
    return CloudIngestor(mock_tm, "refresh_token", log_path), tmp_path

def test_download_file(mock_ingestor):
    """Verify single-file download and local filesystem writing."""
    ingestor, tmp_path = mock_ingestor
    remote_file = "/test.txt"
    local_file = tmp_path / "test.txt"
    
    # Mock the Dropbox response stream
    mock_response = MagicMock()
    mock_response.content = b"data"
    ingestor.dbx.files_download.return_value = (None, mock_response)
    
    ingestor.download_file(remote_file, local_file)
    
    assert local_file.exists()
    assert local_file.read_text() == "data"

@patch("dropbox.Dropbox")
def test_cloud_ingestor_recursive_sync(mock_dbx_class):
    """
    Verify recursion, path reconstruction, and file extension filtering.
    This test simulates a paginated API response from Dropbox.
    """
    # 1. Setup Dependency Injection
    mock_tm = MagicMock(spec=TokenManager)
    mock_tm.refresh_access_token.return_value = "fake_access_token"
    mock_dbx = mock_dbx_class.return_value
    
    # Page 1: A valid file in a subfolder
    page1 = MagicMock()
    file_valid = MagicMock(spec=dropbox.files.FileMetadata)
    file_valid.name = "simulation_01.h5"
    file_valid.path_lower = "/remote/case_01/simulation_01.h5"
    page1.entries = [file_valid]
    page1.has_more = True
    page1.cursor = "next_page_token"
    
    # Page 2: A folder and an invalid extension
    page2 = MagicMock()
    folder_entry = MagicMock(spec=dropbox.files.FolderMetadata)
    folder_entry.path_lower = "/remote/case_02"
    file_invalid = MagicMock(spec=dropbox.files.FileMetadata)
    file_invalid.name = "notes.txt"
    file_invalid.path_lower = "/remote/notes.txt"
    
    page2.entries = [folder_entry, file_invalid]
    page2.has_more = False
    
    mock_dbx.files_list_folder.return_value = page1
    mock_dbx.files_list_folder_continue.return_value = page2
    mock_dbx.files_download.return_value = (None, MagicMock(content=b"physics_data"))

    # 3. Execute with filesystem mocks
    log_path = Path("test_ingest.log")
    local_base = Path("./local_test_data")
    
    with patch("builtins.open", mock_open()), patch("pathlib.Path.mkdir"):
        ingestor = CloudIngestor(mock_tm, "initial_refresh_token", log_path)
        ingestor.sync("/remote", local_base, [".h5"])
    
    # 4. Assertions
    mock_dbx.files_list_folder.assert_called_once_with("/remote", recursive=True)
    mock_dbx.files_list_folder_continue.assert_called_once_with("next_page_token")
    mock_dbx.files_download.assert_called_once_with(path="/remote/case_01/simulation_01.h5")


# =============================================================================
# 4. Module Execution Entry Point
# =============================================================================

# The main block handles system exit codes and critical failures. 
# We test these paths to ensure robustness in the CI/CD pipeline.

def test_main_critical_error_exit():
    """Verify that failures in the main entry point correctly trigger a system exit."""
    with patch("src.io.download_from_dropbox.argparse.ArgumentParser.parse_args", 
               side_effect=Exception("Critical Failure")):
        with pytest.raises(SystemExit) as e:
            # We trigger the logic by simulating a failure in the main block
            # (Assuming standard execution flow inside the if __name__ == "__main__")
            from src.io.download_from_dropbox import main_logic_wrapper
            main_logic_wrapper()
        assert e.value.code == 1