import argparse
import logging
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
    __slots__ = ['dbx', 'logger']

    def __init__(self, token_manager: TokenManager, refresh_token: str, log_path: Path):
        """Deterministic initialization with integrated logging."""
        access_token = token_manager.refresh_access_token(refresh_token)
        self.dbx = dropbox.Dropbox(access_token)
        self.logger = self._setup_logger(log_path)

    def _setup_logger(self, log_path: Path) -> logging.Logger:
        """Configures dual-stream logging (Console + File)."""
        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            # File logger for persistence
            file_handler = logging.FileHandler(log_path)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            # Console logger for GitHub Actions visibility
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        return logger

    def upload(self, local_path: Path, dropbox_folder: str):
        """
        Atomic upload operation with explicit path handling and audit logs.
        """
        if not local_path.exists():
            self.logger.error(f"Local file not found: {local_path}")
            raise FileNotFoundError(f"Local file '{local_path}' not found.")

        folder = f"/{dropbox_folder.strip('/')}"
        dropbox_file_path = f"{folder}/{local_path.name}"
        
        self.logger.info(f"Initiating upload to: {dropbox_file_path}")
        
        with open(local_path, "rb") as f:
            self.dbx.files_upload(
                f.read(), 
                dropbox_file_path, 
                mode=dropbox.files.WriteMode.overwrite
            )
        
        self.logger.info(f"✅ Successfully uploaded: {dropbox_file_path}")


def main():
    """Entry point logic with standardized error handling."""
    parser = argparse.ArgumentParser(description="Upload transaction state archive to Dropbox")
    parser.add_argument("--folder", required=True, help="Target Dropbox folder destination")
    parser.add_argument("--filename", required=True, help="Name of the target zip archive file")
    args = parser.parse_args()

    # Logger setup for main context
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("CloudUploader")

    # Environment validation
    app_key = os.environ.get("DROPBOX_APP_KEY")
    app_secret = os.environ.get("DROPBOX_APP_SECRET")
    refresh_token = os.environ.get("DROPBOX_REFRESH_TOKEN")

    if not all([app_key, app_secret, refresh_token]):
        logger.error("CRITICAL: Missing required Dropbox environment variables.")
        sys.exit(1)

    local_path = Path("data/testing-input-output") / args.filename

    try:
        token_manager = TokenManager(client_id=app_key, client_secret=app_secret)
        # Use a default log path for production, tests can override via class instantiation
        uploader = CloudUploader(token_manager, refresh_token, Path("upload_log.txt"))
        
        uploader.upload(local_path, args.folder)
        
    except Exception as e:
        logger.exception("CRITICAL: Cloud upload pipeline transaction failed")
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
