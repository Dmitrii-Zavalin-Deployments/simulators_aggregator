# tests/io/test_state_manager.py

import os
import pytest
from unittest.mock import MagicMock, patch
import dropbox
from src.io.state_manager import _get_required_env, check_file_exists, main

# --- Helper Logic Tests ---

def test_get_required_env_success():
    """
    Narrative: Verify that the environment variable loader correctly
    returns a stripped string when the key exists.
    """
    os.environ["VALID_KEY"] = "  secret_value  "
    
    # We assert that the value is correctly retrieved and whitespace is stripped.
    assert _get_required_env("VALID_KEY") == "secret_value"
    
    # Cleanup
    del os.environ["VALID_KEY"]

def test_get_required_env_missing():
    """
    Narrative: Ensure the system raises EnvironmentError when a key is absent.
    This enforces the 'No-Default' security policy.
    """
    with pytest.raises(EnvironmentError, match="Missing required environment variable"):
        _get_required_env("NON_EXISTENT_KEY")

def test_get_required_env_empty():
    """
    Narrative: Ensure the system raises EnvironmentError when a key exists 
    but contains only whitespace.
    """
    os.environ["EMPTY_KEY"] = "   "
    with pytest.raises(EnvironmentError, match="is empty or whitespace"):
        _get_required_env("EMPTY_KEY")
    del os.environ["EMPTY_KEY"]


# --- Core Logic Tests ---

@patch("dropbox.Dropbox")
def test_check_file_exists_positive(mock_dbx):
    """
    Narrative: Verify that when the Dropbox API returns metadata, 
    the function correctly identifies the file as present.
    """
    # Execution: Call the checker.
    result = check_file_exists(mock_dbx, "folder", "file.txt")
    
    # Audit: The API was invoked and the logic returned True.
    mock_dbx.files_get_metadata.assert_called_once_with("/folder/file.txt")
    assert result is True

@patch("dropbox.Dropbox")
def test_check_file_exists_not_found(mock_dbx):
    """
    Narrative: Verify that a Dropbox ApiError specifically denoting 
    "path not found" is handled gracefully by returning False.
    """
    # Setup: Create a mock ApiError that identifies as a path not found.
    mock_error = MagicMock()
    mock_error.error.is_path.return_value = True
    mock_path = MagicMock()
    mock_path.is_not_found.return_value = True
    mock_error.error.get_path.return_value = mock_path
    
    # We force the mock client to raise this specific error.
    mock_dbx.files_get_metadata.side_effect = dropbox.exceptions.ApiError(
        request_id="123", 
        error=mock_error, 
        user_message_text="not found", 
        user_message_locale="en"
    )
    
    # Audit: Logic identifies this as "File does not exist".
    assert check_file_exists(mock_dbx, "folder", "file.txt") is False

@patch("dropbox.Dropbox")
def test_check_file_exists_other_error(mock_dbx):
    """
    Narrative: Verify that unexpected API errors (e.g., Auth issues)
    are re-raised rather than suppressed.
    """
    # Setup: Mock a generic ApiError
    mock_error = MagicMock()
    
    # CRITICAL FIX: Explicitly set is_path to False
    # Without this, the code thinks it's a "path not found" error and returns False.
    mock_error.is_path.return_value = False 
    
    mock_dbx.files_get_metadata.side_effect = dropbox.exceptions.ApiError(
        request_id="123", 
        error=mock_error, 
        user_message_text="Auth Fail", 
        user_message_locale="en"
    )
    
    # Audit: We expect the error to bubble up.
    with pytest.raises(dropbox.exceptions.ApiError):
        check_file_exists(mock_dbx, "folder", "file.txt")

# --- Main Orchestration Tests ---

@patch("src.io.state_manager.TokenManager")
@patch("src.io.state_manager.dropbox.Dropbox")
@patch("src.io.state_manager.check_file_exists")
def test_main_success_not_found(mock_check, mock_dbx, mock_tm, monkeypatch, capsys):
    """
    Narrative: Verify the execution path when the file does not exist.
    The system should output 'state_status=not_found' (Line 56).
    """
    # 1. Setup required environment
    monkeypatch.setenv("DROPBOX_APP_KEY", "k")
    monkeypatch.setenv("DROPBOX_APP_SECRET", "s")
    monkeypatch.setenv("DROPBOX_REFRESH_TOKEN", "t")
    
    # 2. Mock CLI arguments
    with patch("sys.argv", ["script", "--folder", "f", "--filename", "n"]):
        # 3. Force the existence check to return False
        mock_check.return_value = False 
        
        # 4. Execute
        main()
        
        # 5. Audit: Captured standard output
        captured = capsys.readouterr()
        assert "state_status=not_found" in captured.out

@patch("src.io.state_manager.TokenManager")
def test_main_missing_env(mock_tm, monkeypatch, capsys):
    """
    Narrative: Verify that missing environment variables trigger a clean
    system exit with error diagnostics sent to stderr.
    """
    # Clear env
    monkeypatch.delenv("DROPBOX_APP_KEY", raising=False)
    
    with patch("sys.argv", ["script", "--folder", "f", "--filename", "n"]):
        # Execute and Expect Exit
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1
        
        # Audit: Ensure error went to stderr
        captured = capsys.readouterr()
        assert "CRITICAL ERROR" in captured.err

@patch("src.io.state_manager.TokenManager")
def test_main_unexpected_exception(mock_tm, monkeypatch, capsys):
    """
    Narrative: Verify that unhandled exceptions are caught, reported,
    and result in a non-zero exit code.
    """
    monkeypatch.setenv("DROPBOX_APP_KEY", "k")
    monkeypatch.setenv("DROPBOX_APP_SECRET", "s")
    monkeypatch.setenv("DROPBOX_REFRESH_TOKEN", "t")
    
    # Force an error in instantiation
    mock_tm.side_effect = Exception("Auth Exploded")
    
    with patch("sys.argv", ["script", "--folder", "f", "--filename", "n"]):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1
        
        captured = capsys.readouterr()
        assert "CRITICAL ERROR: Auth Exploded" in captured.err