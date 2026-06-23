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

def get_config():
    """Retrieves environment configuration with defensive stripping."""
    # .strip() prevents errors from hidden newlines in GitHub Secrets
    return {
        "app_key": os.environ.get("DROPBOX_APP_KEY", "").strip(),
        "app_secret": os.environ.get("DROPBOX_APP_SECRET", "").strip(),
        "refresh_token": os.environ.get("DROPBOX_REFRESH_TOKEN", "").strip(),
        "branch": os.environ.get("GITHUB_REF_NAME", "default"),
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
    # Validate keys are not empty strings after stripping
    if not cfg["app_key"] or not cfg["app_secret"] or not cfg["refresh_token"]:
        raise ValueError("Missing or malformed Dropbox credentials in environment.")

    tm = TokenManager(cfg["app_key"], cfg["app_secret"])
    ingestor = CloudIngestor(tm, cfg["refresh_token"], Path("sync_log.txt"))
    
    remote_path = f"/checkpoints/checkpoint_{cfg['branch']}.zip"
    local_dir = Path("data/checkpoint")
    
    logger.info(f"Checking for checkpoint at {remote_path}...")
    
    if not check_exists(ingestor, remote_path):
        logger.warning("No checkpoint found. Proceeding to Cold Start.")
        print("initialized") # Signal to CI/CD
        return

    logger.info("Checkpoint detected. Downloading...")
    ingestor.sync(remote_path, local_dir, ['.zip'])
    logger.info("Import complete.")
    print("restored") # Signal to CI/CD

def run_export():
    cfg = get_config()
    tm = TokenManager(cfg["app_key"], cfg["app_secret"])
    uploader = CloudUploader(tm, cfg["refresh_token"])
    
    local_zip = Path(f"checkpoint_{cfg['branch']}.zip")
    
    logger.info(f"Exporting {local_zip} to Dropbox...")
    uploader.upload(local_zip, "/checkpoints")
    
    logger.info("Export complete.")
    print("exported") # Signal to CI/CD

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
        logger.error(f"Critical failure during {args.action}: {e}")
        sys.exit(1)