# tests/io/test_state_manager.py

import logging
import os
from unittest.mock import MagicMock, patch

import dropbox
import pytest

from src.io.state_manager import _get_required_env, check_file_exists, main

# ==============================================================================
# Helper Logic Tests
# ==============================================================================

def test_get_required_env_success():
    """Verify clean string extraction for valid keys."""
    # We prime the environment with a key containing padding whitespace.
    os.environ["VALID_KEY"] = "  secret_value  "
    
    # We pass the key to our loader and check that leading/trailing spaces are stripped.
    retrieved_val = _get_required_env("VALID_KEY")
    assert retrieved_val == "secret_value"
    
    # We clean up the target environment variables to prevent environment leaks.
    del os.environ["VALID_KEY"]


def test_get_required_env_missing():
    """Verify strict validation errors for missing keys."""
    # We attempt to retrieve a key that is guaranteed to be absent from our environment.
    # The loader must catch this and immediately raise a strict EnvironmentError.
    with pytest.raises(EnvironmentError, match="Missing required environment variable"):
        _get_required_env("NON_EXISTENT_KEY")


def test_get_required_env_empty():
    """Verify validation errors for blank spaces or empty configurations."""
    # We explicitly simulate a key defined only with blank spaces.
    os.environ["EMPTY_KEY"] = "   "
    
    # The application loader must treat whitespace-only configuration values as empty 
    # and fail fast with an EnvironmentError.
    with pytest.raises(EnvironmentError, match="is empty or whitespace"):
        _get_required_env("EMPTY_KEY")
        
    # We tear down the temporary variable.
    del os.environ["EMPTY_KEY"]


# ==============================================================================
# Core Logic Tests
# ==============================================================================

@patch("dropbox.Dropbox")
def test_check_file_exists_positive(mock_dbx):
    """Verify successful tracking when the metadata endpoint confirms a file exists."""
    # We invoke the function with regular arguments to evaluate remote path normalization.
    result = check_file_exists(mock_dbx, "folder", "file.txt")
    
    # The underlying file metadata API must be called with a clean, leading-slash path:
    #     remote_path = "/folder/file.txt"
    mock_dbx.files_get_metadata.assert_called_once_with("/folder/file.txt")
    
    # Since metadata retrieval succeeded without errors, the function returns True.
    assert result is True


@patch("dropbox.Dropbox")
def test_check_file_exists_not_found(mock_dbx):
    """Verify fallback response logic when the remote path does not exist."""
    # We construct a mock representation of an API path exception context.
    mock_error = MagicMock()
    mock_error.is_path.return_value = True
    
    # We mock the nested path locator object to simulate a missing file asset status.
    mock_path = MagicMock()
    mock_path.is_not_found.return_value = True
    mock_error.get_path.return_value = mock_path
    
    # We configure the metadata fetch operation to bubble up a structural ApiError.
    mock_dbx.files_get_metadata.side_effect = dropbox.exceptions.ApiError(
        request_id="123", 
        error=mock_error, 
        user_message_text="not found", 
        user_message_locale="en"
    )
    
    # We run the visibility test. The path error must be caught gracefully and return False.
    result = check_file_exists(mock_dbx, "folder", "file.txt")
    assert result is False


@patch("dropbox.Dropbox")
def test_check_file_exists_other_error(mock_dbx):
    """Verify critical exceptions are re-raised rather than caught."""
    # We stub out a generic exception block that is completely separate from path failures.
    mock_error = MagicMock()
    
    # We force the path verification indicator to return False to skip standard path fallbacks.
    mock_error.is_path.return_value = False 
    
    # We inject the structured error behavior into our client mock pipeline.
    mock_dbx.files_get_metadata.side_effect = dropbox.exceptions.ApiError(
        request_id="123", 
        error=mock_error, 
        user_message_text="Auth Fail", 
        user_message_locale="en"
    )
    
    # The unhandled operational error must exit our function context and bubble straight up.
    with pytest.raises(dropbox.exceptions.ApiError):
        check_file_exists(mock_dbx, "folder", "file.txt")


# ==============================================================================
# Main Orchestration Tests
# ==============================================================================

@patch("src.io.state_manager.TokenManager")
def test_main_missing_env(mock_tm, monkeypatch, caplog):
    """Verify failure paths when environment keys are completely missing."""
    # We wipe the current tracking app key to break initialization logic.
    monkeypatch.delenv("DROPBOX_APP_KEY", raising=False)
    
    # We mimic a manual terminal call executing with standard flags.
    with patch("sys.argv", ["script", "--folder", "f", "--filename", "n"]):
        # The environment checkpoint must trigger a SystemExit with an error code of 1.
        with pytest.raises(SystemExit) as exit_context:
            main()
        assert exit_context.value.code == 1
        
        # We process the current screen buffer streams to ensure standard errors were recorded.
        l_text = caplog.text
        assert "CRITICAL ERROR" in l_text


@patch("src.io.state_manager.TokenManager")
def test_main_unexpected_exception(mock_tm, monkeypatch, caplog):
    """Verify error containment and safe terminations during execution."""
    # We fill out the base initialization elements to satisfy credential processing checks.
    monkeypatch.setenv("DROPBOX_APP_KEY", "k")
    monkeypatch.setenv("DROPBOX_APP_SECRET", "s")
    monkeypatch.setenv("DROPBOX_REFRESH_TOKEN", "t")
    
    # We mimic a runtime authentication explosion when initializing token states.
    mock_tm.side_effect = Exception("Auth Exploded")
    
    # We mock out parameters and step through runtime lifecycle handling loops.
    with patch("sys.argv", ["script", "--folder", "f", "--filename", "n"]):
        # The crash must be handled internally, printing to stderr and exiting with 1.
        with pytest.raises(SystemExit) as exit_context:
            main()
        assert exit_context.value.code == 1
        
        # We ensure standard error buffers captured the full stack trace diagnostic logs.
        l_text = caplog.text
        # logger.exception outputs the log message and the traceback containing the exception message
        assert "CRITICAL ERROR" in l_text
        assert "Auth Exploded" in l_text


@patch("src.io.state_manager.TokenManager")
@patch("src.io.state_manager.dropbox.Dropbox")
@patch("src.io.state_manager.check_file_exists")
def test_main_success_found(mock_check, mock_dbx, mock_tm, monkeypatch, capsys):
    # caplog.set_level(logging.INFO)
    """Verify runtime signal production paths when target files exist."""
    # We assign credentials to fulfill security constraints.
    monkeypatch.setenv("DROPBOX_APP_KEY", "key_value")
    monkeypatch.setenv("DROPBOX_APP_SECRET", "secret_value")
    monkeypatch.setenv("DROPBOX_REFRESH_TOKEN", "token_value")
    
    # We construct a functional array of input flags matching command line operations.
    with patch("sys.argv", ["script_name", "--folder", "simulators", "--filename", "output.zip"]):
        # We mock our checker method to simulate a found asset.
        mock_check.return_value = True
        
        # We run the application main orchestrator workflow.
        main()
        
        # We read the program output stream to confirm our positive target signal was logged.
        l_text = capsys.readouterr().out
        assert "state_status=found" in l_text


@patch("src.io.state_manager.TokenManager")
@patch("src.io.state_manager.dropbox.Dropbox")
@patch("src.io.state_manager.check_file_exists")
def test_main_success_not_found(mock_check, mock_dbx, mock_tm, monkeypatch, capsys):
    # caplog.set_level(logging.INFO)
    """Verify runtime signal production paths when target files are missing."""
    # We assign credentials to fulfill security constraints.
    monkeypatch.setenv("DROPBOX_APP_KEY", "key_value")
    monkeypatch.setenv("DROPBOX_APP_SECRET", "secret_value")
    monkeypatch.setenv("DROPBOX_REFRESH_TOKEN", "token_value")
    
    # We construct a functional array of input flags matching command line operations.
    with patch("sys.argv", ["script_name", "--folder", "simulators", "--filename", "output.zip"]):
        # We mock our checker method to simulate a missing asset.
        mock_check.return_value = False 
        
        # We run the application main orchestrator workflow.
        main()
        
        # We read the program output stream to confirm our negative target signal was logged.
        l_text = capsys.readouterr().out
        assert "state_status=not_found" in l_text
