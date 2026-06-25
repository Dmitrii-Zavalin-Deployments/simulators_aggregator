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
    __slots__ = ['dbx', 'log_path']

    def __init__(self, token_manager: TokenManager, refresh_token: str, log_path: Path):
        """Deterministic initialization via TokenManager dependency."""
        access_token = token_manager.refresh_access_token(refresh_token)
        self.dbx = dropbox.Dropbox(access_token)
        self.log_path = log_path

    def download_file(self, remote_path: str, local_path: Path):
        """Public method to download a specific file."""
        local_path.parent.mkdir(parents=True, exist_ok=True)
        _, res = self.dbx.files_download(path=remote_path)
        with open(local_path, "wb") as f:
            f.write(res.content)
        print(f"✅ Downloaded {remote_path} -> {local_path}")

    def sync(self, source_folder: str, target_folder: Path, allowed_ext: list):
        """Atomic sync operation with recursive discovery and path reconstruction."""
        target_folder.mkdir(parents=True, exist_ok=True)
        src_base = source_folder.lower().rstrip('/')
        
        with open(self.log_path, "a") as log:
            log.write(f"🚀 Ingestion started: {source_folder}\n")
            
            has_more = True
            cursor = None
            
            while has_more:
                result = (self.dbx.files_list_folder_continue(cursor) 
                          if cursor else self.dbx.files_list_folder(source_folder, recursive=True))
                
                for entry in result.entries:
                    if isinstance(entry, dropbox.files.FileMetadata):
                        if not allowed_ext or Path(entry.name).suffix.lower() in allowed_ext:
                            rel_path = os.path.relpath(entry.path_lower, src_base)
                            local_file_path = target_folder / rel_path
                            local_file_path.parent.mkdir(parents=True, exist_ok=True)
                            self._download_file(entry, local_file_path, log)
                    
                    elif isinstance(entry, dropbox.files.FolderMetadata):
                        rel_path = os.path.relpath(entry.path_lower, src_base)
                        (target_folder / rel_path).mkdir(parents=True, exist_ok=True)

                has_more = result.has_more
                cursor = result.cursor
            log.write("🎉 Ingestion complete.\n")

    def _download_file(self, entry, local_path: Path, log):
        """Internal helper for specific file transfer."""
        _, res = self.dbx.files_download(path=entry.path_lower)
        with open(local_path, "wb") as f:
            f.write(res.content)
        log.write(f"✅ Downloaded {entry.path_lower} -> {local_path}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Direct Dropbox Downloader")
    parser.add_argument("--folder", required=True, help="Dropbox folder path")
    parser.add_argument("--filename", required=True, help="File to download")
    args = parser.parse_args()

    try:
        # Enforce No-Default Policy
        tm = TokenManager(
            _get_required_env("DROPBOX_APP_KEY"),
            _get_required_env("DROPBOX_APP_SECRET")
        )
        ingestor = CloudIngestor(
            tm, 
            _get_required_env("DROPBOX_REFRESH_TOKEN"), 
            Path("download_log.txt")
        )

        remote_path = f"/{args.folder.strip('/')}/{args.filename.strip('/')}"
        local_dir = Path("data/testing-input-output")
        
        ingestor.download_file(remote_path, local_dir / args.filename)
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}", file=sys.stderr)
        sys.exit(1)