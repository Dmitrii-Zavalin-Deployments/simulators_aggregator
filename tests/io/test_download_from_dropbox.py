"""
Archivist I/O: Test Suite
-------------------------------------------------------------------------------
This suite validates the Cloud Ingestion Module against the Project Constitution
Protocol. It covers environment enforcement, deterministic authentication,
and atomic file operations.
"""

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import dropbox
import pytest

from src.io.download_from_dropbox import CloudIngestor, _get_required_env, main
from src.io.dropbox_utils import TokenManager

# =============================================================================
# 1. Enforcement of No-Default Policy
# =============================================================================

# The Environment Helper must enforce explicit configuration. 
# We define a test to verify that if a key exists in the environment,
# the system successfully retrieves the string.
def test_get_required_env_success(monkeypatch):
    monkeypatch.setenv("TEST_KEY", "value")
    assert _get_required_env("TEST_KEY") == "value"

# If a key is missing, the system must halt immediately (Rule 0 / No-Default Policy).
# We assert that an EnvironmentError is raised when the key is absent.
def test_get_required_env_missing():
    with pytest.raises(EnvironmentError):
        _get_required_env("NON_EXISTENT_KEY")


# =============================================================================
# 2. Deterministic Authentication (Rule 5)
# =============================================================================

# TokenManager provides the gateway to the cloud. We verify that tokens are
# refreshed deterministically using the provided credentials.
# We simulate a 200 OK response from the POST request and ensure the 
# extracted token matches the mock data.
def test_token_manager_refresh_success():
    tm = TokenManager(client_id="fake_id", client_secret="fake_secret")
    
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"access_token": "new_shiny_token"}
        
        token = tm.refresh_access_token("refresh_me")
        assert token == "new_shiny_token"
        
        # We verify that the payload passed to the request is correct.
        _, kwargs = mock_post.call_args
        assert kwargs['data']['client_id'] == "fake_id"
        assert kwargs['data']['client_secret'] == "fake_secret"

# We must ensure that unauthorized requests (401) trigger a RuntimeError.
def test_token_manager_refresh_failure():
    tm = TokenManager(client_id="fake_id", client_secret="fake_secret")
    
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 401
        mock_post.return_value.text = "Unauthorized"
        
        with pytest.raises(RuntimeError, match="Dropbox Auth Failed"):
            tm.refresh_access_token("bad_token")


# =============================================================================
# 3. CloudIngestor Operational Logic (Rule 8)
# =============================================================================

# The CloudIngestor relies on Dependency Injection. We create a fixture that
# provides a fully initialized ingestor, ensuring we manually override the
# real Dropbox client with a MagicMock to prevent live network calls.
@pytest.fixture
def mock_ingestor(tmp_path):
    mock_tm = MagicMock(spec=TokenManager)
    mock_tm.refresh_access_token.return_value = "fake_token"
    log_path = tmp_path / "download.log"
    
    ingestor = CloudIngestor(mock_tm, "refresh_token", log_path)
    
    # CRITICAL: Overriding the real client to prevent AttributeError
    ingestor.dbx = MagicMock()
    
    return ingestor, tmp_path

# We verify that file downloading correctly writes content to the local filesystem.
def test_download_file(mock_ingestor):
    ingestor, tmp_path = mock_ingestor
    remote_file = "/test.txt"
    local_file = tmp_path / "test.txt"
    
    # We mock the Dropbox response stream content.
    mock_response = MagicMock()
    mock_response.content = b"data"
    ingestor.dbx.files_download.return_value = (None, mock_response)
    
    ingestor.download_file(remote_file, local_file)
    
    assert local_file.exists()
    assert local_file.read_text() == "data"

# We simulate a paginated API response from Dropbox to ensure recursion works.
@patch("dropbox.Dropbox")
def test_cloud_ingestor_recursive_sync(mock_dbx_class):
    # Setup mocks for paginated traversal
    mock_tm = MagicMock(spec=TokenManager)
    mock_tm.refresh_access_token.return_value = "fake_access_token"
    mock_dbx = mock_dbx_class.return_value
    
    # Page 1: A valid simulation file
    page1 = MagicMock()
    file_valid = MagicMock(spec=dropbox.files.FileMetadata)
    file_valid.name = "simulation_01.h5"
    file_valid.path_lower = "/remote/case_01/simulation_01.h5"
    page1.entries = [file_valid]
    page1.has_more = True
    page1.cursor = "next_page_token"
    
    # Page 2: Non-matching file
    page2 = MagicMock()
    page2.entries = []
    page2.has_more = False
    
    mock_dbx.files_list_folder.return_value = page1
    mock_dbx.files_list_folder_continue.return_value = page2
    mock_dbx.files_download.return_value = (None, MagicMock(content=b"physics_data"))

    # Execute sync with filesystem mocks
    log_path = Path("test_ingest.log")
    local_base = Path("./local_test_data")
    
    with patch("builtins.open", mock_open()), patch("pathlib.Path.mkdir"):
        ingestor = CloudIngestor(mock_tm, "initial_refresh_token", log_path)
        ingestor.dbx = mock_dbx
        ingestor.sync("/remote", local_base, [".h5"])
    
    # Assert API call history
    mock_dbx.files_list_folder.assert_called_once_with("/remote", recursive=True)
    mock_dbx.files_download.assert_called_once_with(path="/remote/case_01/simulation_01.h5")


# =============================================================================
# 4. Module Execution Entry Point
# =============================================================================

# The main block must handle system exit codes gracefully.
# We patch the argument parser to trigger a controlled failure, then
# assert that the system exits with code 1 as expected.
def test_main_critical_error_exit():
    with patch("src.io.download_from_dropbox.argparse.ArgumentParser.parse_args", 
               side_effect=Exception("Critical Failure")):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1

def test_main_success_flow(monkeypatch):
    """Verify that main() executes correctly when arguments are valid."""
    # 1. Setup required environment variables
    monkeypatch.setenv("DROPBOX_APP_KEY", "test_key")
    monkeypatch.setenv("DROPBOX_APP_SECRET", "test_secret")
    monkeypatch.setenv("DROPBOX_REFRESH_TOKEN", "test_refresh")

    # 2. Patch dependencies
    with patch("src.io.download_from_dropbox.CloudIngestor") as MockIngestor, \
        patch("src.io.download_from_dropbox.argparse.ArgumentParser.parse_args") as mock_args:
        # Mock the parsed arguments
        mock_args.return_value = MagicMock(folder="my_folder", filename="my_file.txt")
        
        # 3. Execute main
        main()
        
        # 4. Assertions
        MockIngestor.return_value.download_file.assert_called_once()
        # Check if remote path was formatted correctly (based on line 112)
        args, _ = MockIngestor.return_value.download_file.call_args
        assert args[0] == "/my_folder/my_file.txt"

def test_sync_full_coverage(mock_ingestor):
    """Verify folder creation and filtering logic."""
    ingestor, tmp_path = mock_ingestor
    
    # 1. Prepare Mock Entries
    mock_file = MagicMock(spec=dropbox.files.FileMetadata)
    mock_file.name = "data.csv"
    mock_file.path_lower = "/remote/data.csv"
    
    mock_folder = MagicMock(spec=dropbox.files.FolderMetadata)
    mock_folder.path_lower = "/remote/new_dir"
    
    # 2. Mock list_folder to return both
    ingestor.dbx.files_list_folder.return_value = MagicMock(
        entries=[mock_file, mock_folder], 
        has_more=False, 
        cursor=None
    )
    
    # --- FIX STARTS HERE ---
    # Create a mock response object
    mock_response = MagicMock()
    mock_response.content = b"data"
    
    # Return a tuple (None, mock_response) to satisfy the unpacking _, res = ...
    ingestor.dbx.files_download.return_value = (None, mock_response)
    # --- FIX ENDS HERE ---
    
    # 3. Execute sync
    with patch("pathlib.Path.mkdir") as mock_mkdir:
        ingestor.sync("/remote", tmp_path, None)
        
    assert mock_mkdir.called