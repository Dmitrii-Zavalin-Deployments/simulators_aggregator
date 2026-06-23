# tests/io/test_download_from_dropbox.py

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import dropbox
import pytest

from src.io.download_from_dropbox import CloudIngestor
from src.io.dropbox_utils import TokenManager


def test_token_manager_refresh_success():
    """Rule 5: Verify deterministic token refreshing via requests."""
    tm = TokenManager(client_id="fake_id", client_secret="fake_secret")
    
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"access_token": "new_shiny_token"}
        
        token = tm.refresh_access_token("refresh_me")
        assert token == "new_shiny_token"
        
        # Verify Rule 5: Payload contains explicit credentials
        _, kwargs = mock_post.call_args
        assert kwargs['data']['client_id'] == "fake_id"
        assert kwargs['data']['client_secret'] == "fake_secret"

def test_token_manager_refresh_failure():
    """Rule 5: Verify RuntimeError on auth failure (Zero-Default Policy)."""
    tm = TokenManager(client_id="fake_id", client_secret="fake_secret")
    
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 401
        mock_post.return_value.text = "Unauthorized"
        
        # Updated match to reflect the latest error string in dropbox_utils.py
        with pytest.raises(RuntimeError, match="Dropbox Auth Failed"):
            tm.refresh_access_token("bad_token")

@patch("dropbox.Dropbox")
def test_cloud_ingestor_recursive_sync(mock_dbx_class):
    """Rule 10: Verify recursion, path reconstruction, and filtering."""
    
    # 1. Setup Dependency Injection
    mock_tm = MagicMock(spec=TokenManager)
    mock_tm.refresh_access_token.return_value = "fake_access_token"
    mock_dbx = mock_dbx_class.return_value
    
    # Page 1: A valid file in a subfolder
    page1 = MagicMock()
    file_valid = MagicMock(spec=dropbox.files.FileMetadata)
    file_valid.name = "simulation_01.h5"
    # Note: path_lower must include the source folder to test relpath logic
    file_valid.path_lower = "/remote/case_01/simulation_01.h5"
    page1.entries = [file_valid]
    page1.has_more = True
    page1.cursor = "next_page_token"
    
    # Page 2: A folder metadata entry and an invalid file extension
    page2 = MagicMock()
    folder_entry = MagicMock(spec=dropbox.files.FolderMetadata)
    folder_entry.path_lower = "/remote/case_02"
    
    file_invalid = MagicMock(spec=dropbox.files.FileMetadata)
    file_invalid.name = "notes.txt"
    file_invalid.path_lower = "/remote/notes.txt"
    
    page2.entries = [folder_entry, file_invalid]
    page2.has_more = False
    
    # Mocking Dropbox responses
    mock_dbx.files_list_folder.return_value = page1
    mock_dbx.files_list_folder_continue.return_value = page2
    mock_dbx.files_download.return_value = (None, MagicMock(content=b"physics_data"))

    # 3. Execute
    log_path = Path("test_ingest.log")
    local_base = Path("./local_test_data")
    
    # Use patch to prevent actual filesystem I/O during test
    with patch("builtins.open", mock_open()), \
         patch("pathlib.Path.mkdir"):
        
        ingestor = CloudIngestor(mock_tm, "initial_refresh_token", log_path)
        # Syncing /remote with .h5 filter
        ingestor.sync("/remote", local_base, [".h5"])
    
    # 4. Assertions
    # Verify Rule 8: files_list_folder called with recursive=True
    mock_dbx.files_list_folder.assert_called_once_with("/remote", recursive=True)
    
    # Verify Pagination
    mock_dbx.files_list_folder_continue.assert_called_once_with("next_page_token")
    
    # Verify Path Reconstruction logic:
    # rel_path = os.path.relpath("/remote/case_01/simulation_01.h5", "/remote")
    # should result in "case_01/simulation_01.h5"
    # We check if files_download was called for the correct path
    mock_dbx.files_download.assert_called_once_with(path="/remote/case_01/simulation_01.h5")