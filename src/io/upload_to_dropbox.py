#!/usr/bin/env python3
"""
Archivist I/O: Cloud Upload Module.
"""
import argparse
import os
import sys
from pathlib import Path
import dropbox
from src.io.dropbox_utils import TokenManager


class CloudUploader:
    """
    Handles secure uploading of simulation artifacts.
    Uses __slots__ to minimize memory footprint.
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
            # Using f.read() is optimal for stateless transaction Zips
            self.dbx.files_upload(
                f.read(), 
                dropbox_file_path, 
                mode=dropbox.files.WriteMode.overwrite
            )
        
        print(f"✅ Successfully uploaded: {dropbox_file_path}")


def main():
    parser = argparse.ArgumentParser(description="Upload transaction state archive to Dropbox")
    parser.add_argument("--folder", required=True, help="Target Dropbox folder destination")
    parser.add_argument("--filename", required=True, help="Name of the target zip archive file")
    args = parser.parse_args()

    # Collect authentication payload from runner environment context
    app_key = os.environ.get("DROPBOX_APP_KEY")
    app_secret = os.environ.get("DROPBOX_APP_SECRET")
    refresh_token = os.environ.get("DROPBOX_REFRESH_TOKEN")

    if not all([app_key, app_secret, refresh_token]):
        print("❌ CRITICAL: Missing required Dropbox environment variables.")
        sys.exit(1)

    # Resolve local path. The workflow zips inside 'data/testing-input-output/' 
    # and returns to repo root before calling this script.
    local_path = Path("data/testing-input-output") / args.filename

    try:
        # Initialize token tracking with correct interface signatures matching dropbox_utils.py
        token_manager = TokenManager(client_id=app_key, client_secret=app_secret)
        uploader = CloudUploader(token_manager, refresh_token)
        
        uploader.upload(local_path, args.folder)
        
    except Exception as e:
        print(f"❌ CRITICAL: Cloud upload pipeline transaction failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()