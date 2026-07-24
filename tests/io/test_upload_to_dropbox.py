# tests/io/test_upload_to_dropbox.py

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import dropbox
import pytest

from src.io.dropbox_utils import TokenManager
from src.io.upload_to_dropbox import CloudUploader


@patch("dropbox.Dropbox")
def test_cloud_uploader_success(mock_dbx_class, tmp_path):
    """
    Narrative: Verify that the CloudUploader successfully handles dependency
    injection and executes an atomic upload with normalized paths.
    """
    
    # We initialize the TokenManager mock to return a deterministic access token.
    mock_tm = MagicMock(spec=TokenManager)
    mock_tm.refresh_access_token.return_value = "fake_access_token"
    
    # We capture the Dropbox client instance to verify API calls later.
    mock_dbx = mock_dbx_class.return_value
    
    # We instantiate the Uploader using Dependency Injection.
    # The log_path is provided via the pytest 'tmp_path' fixture for thread safety.
    uploader = CloudUploader(mock_tm, "initial_refresh_token", tmp_path / "test.log")
    
    # We define our test artifact and its payload.
    local_file = Path("navier_stokes_output.zip")
    binary_data = b"simulation_results_payload"
    
    # We define a "dirty" folder path to test the module's normalization logic.
    # The expected behavior is that '//simulators//' becomes '/simulators/'.
    dirty_folder_input = "//simulators//"
    
    # We mock the file system interaction to verify the upload operation.
    with patch.object(Path, "exists", return_value=True), \
        patch("builtins.open", mock_open(read_data=binary_data)):
        uploader.upload(local_file, dirty_folder_input)
            
    # Forensic Audit:
    # We verify the Dropbox client interaction contract:
    # 1. Ensure a file upload was attempted.
    mock_dbx.files_upload.assert_called_once()
    
    # 2. Extract the call arguments to inspect binary data and path formatting.
    args, kwargs = mock_dbx.files_upload.call_args
    
    # 3. Assert that the payload remains untainted:
    assert args[0] == binary_data
    
    # 4. Assert that the path was successfully normalized:
    assert args[1] == "/simulators/navier_stokes_output.zip"
    
    # 5. Verify compliance with Rule 8 (Overwrite mode):
    assert kwargs['mode'] == dropbox.files.WriteMode.overwrite


def test_cloud_uploader_file_not_found(tmp_path):
    """
    Narrative: Ensure the system maintains zero-debt execution by failing 
    immediately if the local file is missing, preventing unnecessary network calls.
    """
    
    # We setup the TokenManager to ensure construction succeeds.
    mock_tm = MagicMock(spec=TokenManager)
    mock_tm.refresh_access_token.return_value = "valid_token"
    
    # We construct the uploader.
    uploader = CloudUploader(mock_tm, "some_token", tmp_path / "test.log")
    
    # We attempt to upload a file that does not exist on disk.
    fake_path = Path("/tmp/non_existent_solver_output_9999.zip")
    
    # We assert that a FileNotFoundError is raised, adhering to the fail-fast protocol.
    with pytest.raises(FileNotFoundError, match="not found"):
        uploader.upload(fake_path, "/remote")


@patch("dropbox.Dropbox")
def test_cloud_uploader_constructor_auth_failure(mock_dbx_class, tmp_path):
    """
    Narrative: Verify that the uploader fails immediately during instantiation 
    if the TokenManager cannot refresh the authentication credentials.
    """
    
    mock_tm = MagicMock(spec=TokenManager)
    
    # We simulate a systemic failure in the authentication handshake.
    mock_tm.refresh_access_token.side_effect = RuntimeError("Dropbox Auth Failed")
    
    # We verify that the constructor propagates the failure, preventing object creation.
    with pytest.raises(RuntimeError, match="Dropbox Auth Failed"):
        CloudUploader(mock_tm, "bad_refresh_token", tmp_path / "test.log")


def test_main_missing_env_vars(monkeypatch):
    """
    Narrative: Validate the environment guardrails. The system must exit
    if the required Dropbox application keys are absent from the environment.
    """
    
    # We explicitly clear the environment variable to trigger the error path.
    monkeypatch.delenv("DROPBOX_APP_KEY", raising=False)
    
    # We mock the CLI parser to simulate an invocation.
    with patch("src.io.upload_to_dropbox.argparse.ArgumentParser.parse_args") as mock_args:
        mock_args.return_value = MagicMock(folder="test", filename="test.zip")
        
        # We assert that the system exits with error code 1.
        with pytest.raises(SystemExit) as e:
            from src.io.upload_to_dropbox import main
            main()
        assert e.value.code == 1


def test_main_success_flow(monkeypatch):
    """
    Narrative: Verify the standard execution flow. When all environment 
    configurations are met, the main orchestrator should trigger the upload.
    """
    
    # We populate the environment with required credentials.
    monkeypatch.setenv("DROPBOX_APP_KEY", "key")
    monkeypatch.setenv("DROPBOX_APP_SECRET", "secret")
    monkeypatch.setenv("DROPBOX_REFRESH_TOKEN", "token")
    
    # We isolate the dependencies.
    with patch("src.io.upload_to_dropbox.argparse.ArgumentParser.parse_args") as mock_args, \
         patch("src.io.upload_to_dropbox.CloudUploader") as MockUploader:
        
        mock_args.return_value = MagicMock(folder="target", filename="data.zip")
        instance = MockUploader.return_value
        
        # We invoke the entry point.
        from src.io.upload_to_dropbox import main
        main()
        
        # We confirm that orchestration occurred:
        MockUploader.assert_called_once()
        instance.upload.assert_called_once()


def test_main_exception_handling(monkeypatch):
    """
    Narrative: Ensure that unexpected failures during the upload process
    are caught and result in a clean system exit (status 1).
    """
    
    # Setup standard environment credentials.
    monkeypatch.setenv("DROPBOX_APP_KEY", "key")
    monkeypatch.setenv("DROPBOX_APP_SECRET", "secret")
    monkeypatch.setenv("DROPBOX_REFRESH_TOKEN", "token")
    
    with patch("src.io.upload_to_dropbox.argparse.ArgumentParser.parse_args") as mock_args, \
         patch("src.io.upload_to_dropbox.CloudUploader") as MockUploader:
        
        mock_args.return_value = MagicMock(folder="target", filename="data.zip")
        
        # We force an exception to simulate a runtime failure.
        MockUploader.return_value.upload.side_effect = Exception("Critical Failure")
        
        # We assert the system handles the crash gracefully.
        with pytest.raises(SystemExit) as e:
            from src.io.upload_to_dropbox import main
            main()
        assert e.value.code == 1