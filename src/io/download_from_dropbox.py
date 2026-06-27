"""
Archivist I/O: Cloud Ingestion Module.

Compliance:
- Rule 0 (Law of Performance): Uses __slots__ for memory efficiency.
- Rule 5 (Deterministic Init): Relies on injected TokenManager.
- Rule 8 (API Minimalism): Single-responsibility ingestion logic.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import dropbox
from src.io.dropbox_utils import TokenManager

def _get_required_env(key: str) -> str:
    """Helper to enforce No-Default policy for environment variables."""
    val = os.environ.get(key)
    if val is None or not val.strip():
        raise EnvironmentError(f"Missing required environment variable: {key}")
    return val.strip()

class CloudIngestor:
    """
    Handles secure synchronization of simulation artifacts.
    Uses __slots__ to minimize memory footprint during heavy I/O.
    """
    __slots__ = ['dbx', 'logger']
    def __init__(self, token_manager, refresh_token, log_path):
        access_token = token_manager.refresh_access_token(refresh_token)
        self.dbx = dropbox.Dropbox(access_token)
        self.logger = self._setup_logger(log_path)

    def _setup_logger(self, log_path):
        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler = logging.FileHandler(log_path)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        return logger

    def download_file(self, remote_path, local_path):
        local_path.parent.mkdir(parents=True, exist_ok=True)
        _, res = self.dbx.files_download(path=remote_path)
        with open(local_path, "wb") as f:
            f.write(res.content)
        self.logger.info(f"✅ Downloaded {remote_path} -> {local_path}")

def main():
    """Entry point logic."""
    parser = argparse.ArgumentParser(description="Direct Dropbox Downloader")
    parser.add_argument("--folder", required=True, help="Dropbox folder path")
    parser.add_argument("--filename", required=True, help="File to download")
    args = parser.parse_args()

    try:
        tm = TokenManager(_get_required_env("DROPBOX_APP_KEY"), _get_required_env("DROPBOX_APP_SECRET"))
        ingestor = CloudIngestor(tm, _get_required_env("DROPBOX_REFRESH_TOKEN"), Path("download_log.txt"))
        remote_path = f"/{args.folder.strip('/')}/{args.filename.strip('/')}"
        local_dir = Path("data/testing-input-output")
        ingestor.download_file(remote_path, local_dir / args.filename)
    except Exception as e:
        logging.getLogger("CloudIngestor").error(f"CRITICAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":  # pragma: no cover
    main()