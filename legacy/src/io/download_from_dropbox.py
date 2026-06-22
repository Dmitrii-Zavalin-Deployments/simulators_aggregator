# src/io/download_from_dropbox.py

"""
Archivist I/O: Cloud Ingestion Module.

Compliance:
- Rule 0 (Law of Performance): Uses __slots__ for memory efficiency.
- Rule 5 (Deterministic Init): Relies on injected TokenManager.
- Rule 8 (API Minimalism): Single-responsibility ingestion logic.
"""

import os
import logging
from pathlib import Path
from typing import List, Union
import dropbox
from src.io.dropbox_utils import TokenManager

# Configure Logger for Ingestion Traceability
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("Engine.CloudIngestor")

class CloudIngestor:
    """
    Handles secure synchronization of simulation artifacts.
    Uses __slots__ to minimize memory footprint during heavy I/O.
    """
    __slots__ = ['dbx', 'log_path', 'token_manager']

    def __init__(self, token_manager: TokenManager, refresh_token: str, log_path: Union[str, Path]):
        """
        Deterministic initialization via TokenManager dependency.
        """
        self.token_manager = token_manager
        self.log_path = Path(log_path) if isinstance(log_path, str) else log_path
        
        try:
            # Phase C: Authentication Handshake
            access_token = self.token_manager.refresh_access_token(refresh_token)
            self.dbx = dropbox.Dropbox(access_token)
            logger.info("✅ CloudIngestor initialized: Session authenticated.")
        except Exception as e:
            logger.critical(f"❌ Failed to initialize Dropbox session: {e}")
            raise

    def sync(self, source_folder: str, target_folder: Union[str, Path], allowed_ext: List[str]):
        """
        Atomic sync operation with recursive discovery and path reconstruction.
        Ensures the 'Clean Room' sync rule is followed.
        """
        logger.info(f"🚀 Ingestion started: {source_folder}")
        
        # Rule 1: Precision Integrity - Ensure target is a Path object
        if isinstance(target_folder, str):
            target_folder = Path(target_folder)
        
        target_folder.mkdir(parents=True, exist_ok=True)
        
        # Normalize source folder for relative path math
        src_base = source_folder.lower().rstrip('/')
        if not src_base.startswith('/'):
            src_base = f"/{src_base}"
        
        try:
            cursor = None
            has_more = True
            
            while has_more:
                if cursor:
                    result = self.dbx.files_list_folder_continue(cursor)
                else:
                    result = self.dbx.files_list_folder(source_folder, recursive=True)
                
                for entry in result.entries:
                    # Logic Gate: Identify Files for Ingestion
                    if isinstance(entry, dropbox.files.FileMetadata):
                        ext = Path(entry.name).suffix.lower()
                        
                        # Rule 4 & 5: If allowed_ext is empty [], all files are ingested.
                        if not allowed_ext or ext in allowed_ext:
                            # Calculate relative path from the source root for folder reconstruction
                            rel_path = os.path.relpath(entry.path_lower, src_base)
                            local_file_path = target_folder / rel_path
                            
                            # Ensure local directory structure matches cloud structure
                            local_file_path.parent.mkdir(parents=True, exist_ok=True)
                            self._download_file(entry.path_lower, local_file_path)
                    
                    # Logic Gate: Explicit Folder Reconstruction
                    elif isinstance(entry, dropbox.files.FolderMetadata):
                        rel_path = os.path.relpath(entry.path_lower, src_base)
                        (target_folder / rel_path).mkdir(parents=True, exist_ok=True)

                has_more = result.has_more
                cursor = result.cursor
                
            logger.info(f"🎉 Ingestion complete for {source_folder}")

        except dropbox.exceptions.ApiError as e:
            logger.error(f"❌ Dropbox API Error during sync: {e}")
            raise

    def _download_file(self, dropbox_path: str, local_path: Path):
        """
        Internal helper for specific file transfer.
        Enforces the 'Clean Room' rule by writing in binary mode.
        """
        try:
            metadata, res = self.dbx.files_download(path=dropbox_path)
            # Binary write ensures simulation artifacts (.npy, .h5, .zip) remain uncorrupted.
            with open(local_path, "wb") as f:
                f.write(res.content)
            logger.info(f"📁 Synced: {dropbox_path} -> {local_path}")
        except Exception as e:
            logger.error(f"❌ Failed to download {dropbox_path}: {e}")
            raise