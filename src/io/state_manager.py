import argparse
import logging
import os
import sys

import dropbox

from src.io.dropbox_utils import TokenManager

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


def _get_required_env(key: str) -> str:
    """Helper to enforce No-Default policy."""
    val = os.environ.get(key)
    if val is None:
        raise OSError(f"Missing required environment variable: {key}")
    
    val_stripped = val.strip()
    if not val_stripped:
        raise OSError(f"Environment variable '{key}' is empty or whitespace.")
    
    return val_stripped

def check_file_exists(dbx: dropbox.Dropbox, folder: str, filename: str) -> bool:
    """Checks if file exists using Dropbox Metadata API."""
    # Ensure clean path construction regardless of how inputs are passed
    clean_folder = folder.strip('/')
    clean_filename = filename.strip('/')
    remote_path = f"/{clean_folder}/{clean_filename}"
    
    try:
        dbx.files_get_metadata(remote_path)
        return True
    except dropbox.exceptions.ApiError as e:
        if e.error.is_path() and e.error.get_path().is_not_found():
            return False
        raise

def main():
    # Route all unhandled errors to the logger
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.error(f"CRITICAL ERROR: {exc_value}")
        sys.exit(1)

    sys.excepthook = handle_exception

    # Enforce strict input parameters
    parser = argparse.ArgumentParser(description="Deterministic Dropbox File Existence Checker")
    parser.add_argument("--folder", required=True, help="Target folder in the Dropbox root")
    parser.add_argument("--filename", required=True, help="Target filename to search for")
    args = parser.parse_args()

    # 1. Enforce No-Default Policy for Credentials
    app_key = _get_required_env("DROPBOX_APP_KEY")
    app_secret = _get_required_env("DROPBOX_APP_SECRET")
    refresh_token = _get_required_env("DROPBOX_REFRESH_TOKEN")

    # 2. Authenticate
    tm = TokenManager(app_key, app_secret)
    access_token = tm.refresh_access_token(refresh_token)
    dbx = dropbox.Dropbox(access_token)

    # 3. Check Existence & Output CI/CD Signal via logger
    if check_file_exists(dbx, args.folder, args.filename):
        logger.info("state_status=found")
    else:
        logger.info("state_status=not_found")

if __name__ == "__main__":  # pragma: no cover
    main()
