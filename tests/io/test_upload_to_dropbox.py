# tests/io/test_upload_to_dropbox.py

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import dropbox
import pytest

from src.io.dropbox_utils import TokenManager
from src.io.upload_to_dropbox import CloudUploader


@patch("dropbox.Dropbox")
def test_cloud_uploader_success(mock_dbx_class):
    """Rule 5 & 10: Verify DI-based initialization and atomic upload."""
    
    # 1. Setup Deterministic Mocks (Rule 5)
    mock_tm = MagicMock(spec=TokenManager)
    mock_tm.refresh_access_token.return_value = "fake_access_token"
    mock_dbx = mock_dbx_class.return_value
    
    # 2. Instantiate via Dependency Injection
    uploader = CloudUploader(mock_tm, "initial_refresh_token")
    
    local_file = Path("navier_stokes_output.zip")
    binary_data = b"simulation_results_payload"
    
    # 3. Execute Atomic Upload
    # We test with a "dirty" folder string to verify the path normalization logic
    dirty_folder_input = "//simulators//"
    
    with patch.object(Path, "exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=binary_data)):
            uploader.upload(local_file, dirty_folder_input)
            
    # 4. Forensic Audit (Rule 10)
    # Ensure the Dropbox client was called with the correct binary and normalized path
    mock_dbx.files_upload.assert_called_once()
    args, kwargs = mock_dbx.files_upload.call_args
    
    # args[0] is the binary data
    assert args[0] == binary_data
    
    # args[1] is the remote path. 
    # Verification: Logic should have stripped the // and normalized it.
    assert args[1] == "/simulators/navier_stokes_output.zip"
    
    # Verify Rule 8: Explicit overwrite mode was used
    assert kwargs['mode'] == dropbox.files.WriteMode.overwrite


def test_cloud_uploader_file_not_found():
    """Rule 2: Ensure zero-debt execution by failing fast on missing files."""
    
    # Setup mock with valid token so we don't fail at the constructor
    mock_tm = MagicMock(spec=TokenManager)
    mock_tm.refresh_access_token.return_value = "valid_token"
    
    uploader = CloudUploader(mock_tm, "some_token")
    
    # Use a path that definitely won't exist locally
    fake_path = Path("/tmp/non_existent_solver_output_9999.zip")
    
    # Logic should raise FileNotFoundError before attempting Dropbox API calls
    with pytest.raises(FileNotFoundError, match="not found"):
        uploader.upload(fake_path, "/remote")


@patch("dropbox.Dropbox")
def test_cloud_uploader_constructor_auth_failure(mock_dbx_class):
    """Rule 5: Verify that uploader fails immediately if token refresh fails."""
    
    mock_tm = MagicMock(spec=TokenManager)
    # Simulate a failure in the TokenManager
    mock_tm.refresh_access_token.side_effect = RuntimeError("Dropbox Auth Failed")
    
    with pytest.raises(RuntimeError, match="Dropbox Auth Failed"):
        CloudUploader(mock_tm, "bad_refresh_token")