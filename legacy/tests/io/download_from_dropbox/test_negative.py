# tests/io/download_from_dropbox/test_negative.py

import pytest
import dropbox
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.io.download_from_dropbox import CloudIngestor

class TestCloudIngestor:
    @pytest.fixture
    def mock_token_manager(self):
        tm = MagicMock()
        tm.refresh_access_token.return_value = "mock_access_token"
        return tm

    @pytest.fixture
    def ingestor(self, mock_token_manager):
        """
        Fixture that patches the Dropbox class to ensure the instance 
        is a mock before the Ingestor's __init__ completes.
        """
        with patch("dropbox.Dropbox") as mock_dbx_class:
            mock_dbx_class.return_value
            # Initialize with dummy data; self.dbx will be our mock_instance
            ci = CloudIngestor(mock_token_manager, "mock_refresh_token", "/tmp/log.txt")
            return ci

    # --- SECTION 1: INITIALIZATION (Lines 40-47) ---

    def test_init_success(self, mock_token_manager):
        with patch("dropbox.Dropbox") as mock_dbx:
            ingestor = CloudIngestor(mock_token_manager, "token", "log.txt")
            mock_dbx.assert_called_once_with("mock_access_token")
            assert isinstance(ingestor.log_path, Path)

    def test_init_failure_raises(self, mock_token_manager):
        mock_token_manager.refresh_access_token.side_effect = Exception("Auth Failed")
        with pytest.raises(Exception, match="Auth Failed"):
            CloudIngestor(mock_token_manager, "token", "log.txt")

    # --- SECTION 2: SYNC LOGIC (Lines 49-105) ---

    def test_sync_normalization_and_recursion(self, ingestor, tmp_path):
        """Covers Lines 58, 65, 80-90, 94-95."""
        # Mocking the Dropbox result structure
        mock_result = MagicMock()
        mock_result.has_more = False
        mock_result.cursor = "v1"
        
        # File Metadata Mock (Line 79)
        file_entry = MagicMock(spec=dropbox.files.FileMetadata)
        file_entry.name = "simulation.npy"
        file_entry.path_lower = "/data/simulation.npy"
        
        # Folder Metadata Mock (Line 93)
        folder_entry = MagicMock(spec=dropbox.files.FolderMetadata)
        folder_entry.path_lower = "/data/logs"
        
        mock_result.entries = [file_entry, folder_entry]
        ingestor.dbx.files_list_folder.return_value = mock_result

        with patch.object(CloudIngestor, "_download_file") as mock_down:
            # 'data' without slash tests normalization (Line 65)
            ingestor.sync("data", str(tmp_path), [".npy"])
            
            # Verify folder reconstruction (Line 95)
            assert (tmp_path / "logs").exists()
            # Verify file download trigger (Line 90)
            mock_down.assert_called_once()

    def test_sync_api_error_handling(self, ingestor, tmp_path):
        """Covers Lines 102-104."""
        # Use positional arguments to avoid SDK signature TypeErrors
        ingestor.dbx.files_list_folder.side_effect = dropbox.exceptions.ApiError(
            "1", MagicMock(), "Rate Limit", None
        )
        with pytest.raises(dropbox.exceptions.ApiError):
            ingestor.sync("/src", tmp_path, [])

    # --- SECTION 3: DOWNLOAD LOGIC (Lines 106-120) ---

    def test_download_file_binary_integrity(self, ingestor, tmp_path):
        """Covers Lines 111-116."""
        target = tmp_path / "test.bin"
        mock_res = MagicMock()
        mock_res.content = b"\x00\xFF\xAA\x55" # Simulation artifact binary data
        
        ingestor.dbx.files_download.return_value = (None, mock_res)

        # Testing Line 114-115 (Binary Write)
        ingestor._download_file("/cloud/test.bin", target)
        
        assert target.read_bytes() == b"\x00\xFF\xAA\x55"

    def test_download_file_failure(self, ingestor, tmp_path):
        """Covers Lines 117-119."""
        ingestor.dbx.files_download.side_effect = Exception("Network Timeout")
        with pytest.raises(Exception, match="Network Timeout"):
            ingestor._download_file("/path", tmp_path / "fail.bin")