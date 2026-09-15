# tests/io/test_upload_to_dropbox.py
"""
Literate Test Suite: CloudUploader Persistence & Strategy Dispatch
==================================================================
Narrative verification ensuring zero-debt execution, strict path normalization,
and payload-size-conditioned execution routing (single-shot <= 150MB vs chunked sessions > 150MB).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import dropbox
import pytest

from src.io.dropbox_utils import TokenManager
from src.io.upload_to_dropbox import CloudUploader


def test_cloud_uploader_single_upload_success(tmp_path):
    """
    Narrative: For a payload size S below the single-upload threshold limit 
        L_single = 150 * 1024 * 1024 bytes,
    the uploader must invoke atomic single-request upload via dbx.files_upload
    with normalized destination paths.
    """
    # Setup deterministic mock token management
    mock_tm = MagicMock(spec=TokenManager)
    mock_tm.refresh_access_token.return_value = "fake_access_token"

    with patch("dropbox.Dropbox") as mock_dbx_class:
        mock_dbx = mock_dbx_class.return_value
        
        # Instantiate uploader dependency injection container
        uploader = CloudUploader(mock_tm, "initial_refresh_token", tmp_path / "test.log")

        # Materialize local test artifact inside isolated tmp_path namespace
        local_file = tmp_path / "navier_stokes_output.zip"
        binary_data = b"simulation_results_payload"
        local_file.write_bytes(binary_data)

        # Dirty path invariant check: '//simulators//' -> '/simulators/'
        dirty_folder_input = "//simulators//"
        expected_remote_path = "/simulators/navier_stokes_output.zip"

        # Execute target upload behavior
        uploader.upload(local_file, dirty_folder_input)

        # Verification audit of client interactions
        mock_dbx.files_upload.assert_called_once()
        args, kwargs = mock_dbx.files_upload.call_args

        # Verify payload byte integrity and path mapping
        assert args[0] == binary_data
        assert args == expected_remote_path
        assert kwargs['mode'] == dropbox.files.WriteMode.overwrite


def test_cloud_uploader_chunked_session_dispatch_for_large_payload(tmp_path):
    """
    Narrative: When payload size S exceeds threshold limit 
        L_single = 150,286,400 bytes,
    dispatch logic must split stream into 8MB chunks using 
    upload_session_start, sequential append_v2 calls, and session_finish.
    """
    mock_tm = MagicMock(spec=TokenManager)
    mock_tm.refresh_access_token.return_value = "fake_access_token"

    with patch("dropbox.Dropbox") as mock_dbx_class:
        mock_dbx = mock_dbx_class.return_value
        
        # Mock session start return contract
        mock_start_res = MagicMock()
        mock_start_res.session_id = "test_session_id_999"
        mock_dbx.files_upload_session_start.return_value = mock_start_res

        uploader = CloudUploader(mock_tm, "token", tmp_path / "chunk_test.log")
        # Temporarily override single upload limit threshold for test isolation
        uploader.SINGLE_UPLOAD_LIMIT = 10  # 10 bytes threshold

        local_file = tmp_path / "large_archive.zip"
        # Payload size = 25 bytes > 10 bytes threshold (forces chunking path)
        large_binary_data = b"0123456789012345678904321"
        local_file.write_bytes(large_binary_data)

        uploader.upload(local_file, "/archive_vault")

        # Confirm chunked session life-cycle invoked
        mock_dbx.files_upload_session_start.assert_called_once()
        assert mock_dbx.files_upload_session_append_v2.call_count >= 1
        mock_dbx.files_upload_session_finish.assert_called_once()


def test_cloud_uploader_file_not_found_fails_fast(tmp_path):
    """
    Narrative: Zero-debt execution invariant — referencing a non-existent local file path 
    must raise FileNotFoundError immediately prior to network or session allocation.
    """
    mock_tm = MagicMock(spec=TokenManager)
    mock_tm.refresh_access_token.return_value = "valid_token"

    uploader = CloudUploader(mock_tm, "some_token", tmp_path / "test.log")
    fake_path = tmp_path / "non_existent_solver_output_9999.zip"

    with pytest.raises(FileNotFoundError, match="not found"):
        uploader.upload(fake_path, "/remote")


@patch("dropbox.Dropbox")
def test_cloud_uploader_constructor_auth_failure(mock_dbx_class, tmp_path):
    """
    Narrative: Propagation check — if TokenManager refresh raises RuntimeError,
    object construction must abort and re-raise.
    """
    mock_tm = MagicMock(spec=TokenManager)
    mock_tm.refresh_access_token.side_effect = RuntimeError("Dropbox Auth Failed")

    with pytest.raises(RuntimeError, match="Dropbox Auth Failed"):
        CloudUploader(mock_tm, "bad_refresh_token", tmp_path / "test.log")


def test_main_missing_env_vars(monkeypatch):
    """
    Narrative: Environment guardrail check — CLI entry point must exit with status code 1
    when required DROPBOX_APP_KEY variables are absent.
    """
    monkeypatch.delenv("DROPBOX_APP_KEY", raising=False)

    with patch("src.io.upload_to_dropbox.argparse.ArgumentParser.parse_args") as mock_args:
        mock_args.return_value = MagicMock(folder="test", filename="test.zip")
        
        with pytest.raises(SystemExit) as e:
            from src.io.upload_to_dropbox import main
            main()
        assert e.value.code == 1


def test_main_success_flow(monkeypatch, tmp_path):
    """
    Narrative: End-to-end CLI orchestrator verification — valid environment and mock CLI args 
    must instantiate CloudUploader and invoke upload().
    """
    monkeypatch.setenv("DROPBOX_APP_KEY", "key")
    monkeypatch.setenv("DROPBOX_APP_SECRET", "secret")
    monkeypatch.setenv("DROPBOX_REFRESH_TOKEN", "token")

    with patch("src.io.upload_to_dropbox.argparse.ArgumentParser.parse_args") as mock_args, \
         patch("src.io.upload_to_dropbox.CloudUploader") as MockUploader, \
         patch("src.io.upload_to_dropbox.Path") as mock_path_cls:
        
        mock_args.return_value = MagicMock(folder="target", filename="data.zip")
        instance = MockUploader.return_value

        from src.io.upload_to_dropbox import main
        main()

        MockUploader.assert_called_once()
        instance.upload.assert_called_once()


def test_main_exception_handling(monkeypatch):
    """
    Narrative: Safety boundary check — unexpected crash inside upload execution 
    must be trapped by logger.exception and exit with code 1.
    """
    monkeypatch.setenv("DROPBOX_APP_KEY", "key")
    monkeypatch.setenv("DROPBOX_APP_SECRET", "secret")
    monkeypatch.setenv("DROPBOX_REFRESH_TOKEN", "token")

    with patch("src.io.upload_to_dropbox.argparse.ArgumentParser.parse_args") as mock_args, \
         patch("src.io.upload_to_dropbox.CloudUploader") as MockUploader:
        
        mock_args.return_value = MagicMock(folder="target", filename="data.zip")
        MockUploader.return_value.upload.side_effect = Exception("Critical Failure")

        with pytest.raises(SystemExit) as e:
            from src.io.upload_to_dropbox import main
            main()
        assert e.value.code == 1
