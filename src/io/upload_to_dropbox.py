# src/io/upload_to_dropbox.py

"""
Archivist I/O: Cloud Upload Module.
"""

from pathlib import Path

import dropbox

from src.io.dropbox_utils import TokenManager


class CloudUploader:
    """
    Handles secure uploading of simulation artifacts.
    Uses __slots__ per Rule 0 to minimize memory footprint.
    """
    __slots__ = ['dbx']

    def __init__(self, token_manager: TokenManager, refresh_token: str):
        access_token = token_manager.refresh_access_token(refresh_token)
        self.dbx = dropbox.Dropbox(access_token)

    def upload(self, local_path: Path, dropbox_folder: str):
        """
        Atomic upload operation with explicit path handling.
        """
        if not local_path.exists():
            raise FileNotFoundError(f"Local file '{local_path}' not found.")

        # Ensure dropbox_folder starts with a slash and does not end with one
        folder = f"/{dropbox_folder.strip('/')}"
        dropbox_file_path = f"{folder}/{local_path.name}"
        
        with open(local_path, "rb") as f:
            # Rule 0: Using f.read() is fine for small/medium Zips, 
            # for multi-GB files, we would use session_upload.
            self.dbx.files_upload(
                f.read(), 
                dropbox_file_path, 
                mode=dropbox.files.WriteMode.overwrite
            )
        
        print(f"✅ Successfully uploaded: {dropbox_file_path}")