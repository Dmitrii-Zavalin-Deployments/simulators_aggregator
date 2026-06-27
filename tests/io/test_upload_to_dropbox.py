# tests/io/test_upload_to_dropbox.py

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import dropbox
import pytest

from src.io.dropbox_utils import TokenManager
from src.io.upload_to_dropbox import CloudUploader


@patch("dropbox.Dropbox")
def test_cloud_uploader_success(mock_dbx_class, tmp_path):
    """Rule 5 & 10: Verify DI-based initialization and atomic upload."""
    
    # 1. Setup Deterministic Mocks (Rule 5)
    mock_tm = MagicMock(spec=TokenManager)
    mock_tm.refresh_access_token.return_value = "fake_access_token"
    mock_dbx = mock_dbx_class.return_value
    
    # 2. Instantiate via Dependency Injection
    uploader = CloudUploader(mock_tm, "initial_refresh_token", tmp_path / "test.log")
    
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


def test_cloud_uploader_file_not_found(tmp_path):
    """Rule 2: Ensure zero-debt execution by failing fast on missing files."""
    
    # Setup mock with valid token so we don't fail at the constructor
    mock_tm = MagicMock(spec=TokenManager)
    mock_tm.refresh_access_token.return_value = "valid_token"
    
    uploader = CloudUploader(mock_tm, "some_token", tmp_path / "test.log")
    
    # Use a path that definitely won't exist locally
    fake_path = Path("/tmp/non_existent_solver_output_9999.zip")
    
    # Logic should raise FileNotFoundError before attempting Dropbox API calls
    with pytest.raises(FileNotFoundError, match="not found"):
        uploader.upload(fake_path, "/remote")


@patch("dropbox.Dropbox")
def test_cloud_uploader_constructor_auth_failure(mock_dbx_class, tmp_path):
    """Rule 5: Verify that uploader fails immediately if token refresh fails."""
    
    mock_tm = MagicMock(spec=TokenManager)
    # Simulate a failure in the TokenManager
    mock_tm.refresh_access_token.side_effect = RuntimeError("Dropbox Auth Failed")
    
    with pytest.raises(RuntimeError, match="Dropbox Auth Failed"):
        CloudUploader(mock_tm, "bad_refresh_token", tmp_path / "test.log")

def test_main_missing_env_vars(monkeypatch):
    """
    Rule: Ensure system exits if required environment variables are missing.
    We test the branch: if not all([app_key, app_secret, refresh_token]):
    """
    # 1. Clear environment to force validation failure
    monkeypatch.delenv("DROPBOX_APP_KEY", raising=False)
    
    # 2. Mock argparse to simulate CLI input
    with patch("src.io.upload_to_dropbox.argparse.ArgumentParser.parse_args") as mock_args:
        mock_args.return_value = MagicMock(folder="test", filename="test.zip")
        
        # 3. Assert system exit
        with pytest.raises(SystemExit) as e:
            from src.io.upload_to_dropbox import main
            main()
        assert e.value.code == 1


def test_main_success_flow(monkeypatch):
    """
    Rule: Verify standard execution flow when all environment variables are present.
    """
    # 1. Set required environment
    monkeypatch.setenv("DROPBOX_APP_KEY", "key")
    monkeypatch.setenv("DROPBOX_APP_SECRET", "secret")
    monkeypatch.setenv("DROPBOX_REFRESH_TOKEN", "token")
    
    # 2. Mock dependencies
    with patch("src.io.upload_to_dropbox.argparse.ArgumentParser.parse_args") as mock_args, \
         patch("src.io.upload_to_dropbox.CloudUploader") as MockUploader:
        
        mock_args.return_value = MagicMock(folder="target", filename="data.zip")
        instance = MockUploader.return_value
        
        # 3. Execute main
        from src.io.upload_to_dropbox import main
        main()
        
        # 4. Verify orchestration
        MockUploader.assert_called_once()
        instance.upload.assert_called_once()


def test_main_exception_handling(monkeypatch):
    """
    Rule: Verify that the catch-all exception block in main() triggers sys.exit(1).
    This exercises lines 85-93 (the try...except block).
    """
    monkeypatch.setenv("DROPBOX_APP_KEY", "key")
    monkeypatch.setenv("DROPBOX_APP_SECRET", "secret")
    monkeypatch.setenv("DROPBOX_REFRESH_TOKEN", "token")
    
    with patch("src.io.upload_to_dropbox.argparse.ArgumentParser.parse_args") as mock_args, \
         patch("src.io.upload_to_dropbox.CloudUploader") as MockUploader:
        
        mock_args.return_value = MagicMock(folder="target", filename="data.zip")
        
        # Force the upload method to crash
        MockUploader.return_value.upload.side_effect = Exception("Critical Failure")
        
        # Assert system exit
        with pytest.raises(SystemExit) as e:
            from src.io.upload_to_dropbox import main
            main()
        assert e.value.code == 1