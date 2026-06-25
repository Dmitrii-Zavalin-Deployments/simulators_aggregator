import os
import logging
import sys
import argparse
from pathlib import Path
import dropbox
from src.io.dropbox_utils import TokenManager
from src.io.download_from_dropbox import CloudIngestor
from src.io.upload_to_dropbox import CloudUploader

# 1. Configure Logging to stderr (keeps stdout clean for CI signals)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("StateManager")

def _get_required_env(key: str) -> str:
    """Helper to enforce No-Default policy."""
    val = os.environ.get(key)
    if val is None:
        raise EnvironmentError(f"Missing required environment variable: {key}")
    
    val_stripped = val.strip()
    if not val_stripped:
        raise EnvironmentError(f"Environment variable '{key}' is empty or whitespace.")
    
    return val_stripped

def get_config():
    """Retrieves environment configuration with strict validation."""
    return {
        "app_key": _get_required_env("DROPBOX_APP_KEY"),
        "app_secret": _get_required_env("DROPBOX_APP_SECRET"),
        "refresh_token": _get_required_env("DROPBOX_REFRESH_TOKEN"),
        "branch": _get_required_env("GITHUB_REF_NAME"),
    }

def check_exists(ingestor, remote_path):
    """Checks if file exists using Metadata API."""
    try:
        ingestor.dbx.files_get_metadata(remote_path)
        return True
    except dropbox.exceptions.ApiError as e:
        if e.error.is_path() and e.error.get_path().is_not_found():
            return False
        raise e

def run_import():
    cfg = get_config()
    tm = TokenManager(cfg["app_key"], cfg["app_secret"])
    ingestor = CloudIngestor(tm, cfg["refresh_token"], Path("sync_log.txt"))
    
    remote_path = f"/checkpoints/checkpoint_{cfg['branch']}.zip"
    local_dir = Path("data/checkpoint")
    
    logger.info(f"Checking for checkpoint at {remote_path}...")
    
    if not check_exists(ingestor, remote_path):
        logger.warning("No checkpoint found. Proceeding to Cold Start.")
        print("state_status=initialized") # CI/CD Signal
        return

    logger.info("Checkpoint detected. Downloading...")
    ingestor.sync(remote_path, local_dir, ['.zip'])
    logger.info("Import complete.")
    print("state_status=restored") # CI/CD Signal

def run_export():
    cfg = get_config()
    tm = TokenManager(cfg["app_key"], cfg["app_secret"])
    uploader = CloudUploader(tm, cfg["refresh_token"])
    
    local_zip = Path(f"checkpoint_{cfg['branch']}.zip")
    
    logger.info(f"Exporting {local_zip} to Dropbox...")
    uploader.upload(local_zip, "/checkpoints")
    
    logger.info("Export complete.")
    print("state_status=exported") # CI/CD Signal

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=["import", "export"], required=True)
    args = parser.parse_args()
    
    try:
        if args.action == "import":
            run_import()
        else:
            run_export()
    except Exception as e:
        # This will catch our custom EnvironmentErrors from get_config
        logger.error(f"Critical failure during {args.action}: {e}")
        sys.exit(1)