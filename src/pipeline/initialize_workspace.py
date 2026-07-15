#!/usr/bin/env python3
# src/pipeline/initialize_workspace.py

import os
import sys
import json
import shutil
import logging
import argparse
from pathlib import Path

# Configure logging early so the self-healing diagnostic block can use it
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("WorkspaceInitializer")

def inspect_and_fix_environment():
    """
    Diagnoses environment mismatches and dynamically repairs sys.path 
    if libraries (like dropbox) are installed in a different Python runtime context.
    """
    logger.info(f"🔍 [ENV] Runtime Interpreter: {sys.executable}")
    logger.info(f"🔍 [ENV] Python Version: {sys.version}")
    
    try:
        import dropbox
        logger.info("✅ [ENV] 'dropbox' is natively importable. Path integrity is healthy.")
        return
    except ImportError:
        logger.warning("⚠️ [ENV] 'dropbox' not found natively. Initiating automatic system-path repair...")

    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    
    # Broad array of common local, virtualenv, and GitHub Actions environments
    paths_to_probe = [
        Path.home() / ".local/lib" / f"python{py_ver}" / "site-packages",
        Path("/opt/hostedtoolcache/Python") / f"3.11.*" / "x64/lib" / f"python{py_ver}" / "site-packages",
        Path("/usr/local/lib") / f"python{py_ver}" / "dist-packages",
        Path("/usr/local/lib") / f"python{py_ver}" / "site-packages",
        Path("./venv/lib") / f"python{py_ver}" / "site-packages",
        Path("./.venv/lib") / f"python{py_ver}" / "site-packages",
    ]

    import glob
    resolved_paths = []
    for candidate in paths_to_probe:
        candidate_str = str(candidate)
        if "*" in candidate_str:
            matches = glob.glob(candidate_str)
            for m in matches:
                resolved_paths.append(Path(m))
        else:
            resolved_paths.append(candidate)

    for p in resolved_paths:
        p_resolved = p.resolve()
        if p_resolved.exists() and str(p_resolved) not in sys.path:
            logger.info(f"🔧 [ENV] Dynamic path recovery: Appending {p_resolved}")
            sys.path.insert(0, str(p_resolved))

    try:
        import dropbox
        logger.info("✅ [ENV] Self-repair successful: 'dropbox' successfully bound to run context.")
    except ImportError as e:
        logger.error(f"❌ [ENV] CRITICAL: 'dropbox' remains missing after recovery sequence. Error: {e}")

# Run environment healing check immediately before custom internal module imports
inspect_and_fix_environment()

# Custom local module imports (safe now that sys.path is normalized)
from src.state.tuner_state import TunerState

def parse_arguments():
    parser = argparse.ArgumentParser(description="ACE Loop Cold Start Workspace Map Initializer")
    parser.add_argument("--repo-path", required=True, help="Path to the pre-cloned repository payload")
    return parser.parse_args()

def fetch_inputs_from_dropbox(target_dir: Path):
    logger.info("Verifying integrity and presence of required pipeline remote data assets...")
    target_dir.mkdir(parents=True, exist_ok=True)

    from src.io.dropbox_utils import TokenManager
    from src.io.download_from_dropbox import CloudIngestor
    
    app_key = os.environ.get("DROPBOX_APP_KEY")
    app_secret = os.environ.get("DROPBOX_APP_SECRET")
    refresh_token = os.environ.get("DROPBOX_REFRESH_TOKEN")
    dropbox_folder = os.environ.get("DROPBOX_FOLDER", "simulators").strip("/")
    
    if not all([app_key, app_secret, refresh_token]):
        raise EnvironmentError("❌ CRITICAL: Missing required Dropbox credentials.")
    
    tm = TokenManager(app_key, app_secret)
    ingestor = CloudIngestor(tm, refresh_token, Path("dropbox_download.log"))
    
    dropbox_base = dropbox_folder.split("/")[0]
    remote_folder_path = f"/{dropbox_base}" if dropbox_base else ""
    
    logger.info(f"Syncing Dropbox folder '{remote_folder_path}' to '{target_dir}'...")
    ingestor.sync(remote_folder_path, target_dir, allowed_ext=[])

def main():
    args = parse_arguments()
    repo_path = Path(args.repo_path)
    branch_name = os.environ.get("GITHUB_REF_NAME", "default_branch")
    
    # 1. Parse local configuration frameworks
    with open(Path("task.json"), 'r') as f:
        task_data = json.load(f)
        
    search_pattern = f"{task_data['pipeline_id']}*"
    manifest_file = list(repo_path.rglob(search_pattern))[0]
    
    with open(manifest_file, 'r') as f:
        manifest_data = json.load(f)
        
    target_config_path = manifest_data.get("config")
    modules_input_output_folder = manifest_data.get("modules_input_output_folder")
    execution_chain = manifest_data.get("execution_chain", [])

    # 2. Build Core Workspace Directories under data/testing-input-output/tuning_<branch>
    workspace_dir = Path("data/testing-input-output") / f"tuning_{branch_name}"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    # 3. Populate Sync Directory Assets
    dropbox_target_folder_name = Path(modules_input_output_folder).name
    dropbox_download_dir = workspace_dir / dropbox_target_folder_name
    fetch_inputs_from_dropbox(dropbox_download_dir)
            
    # 4. Stage Unified Config Blueprint
    configs_dir = workspace_dir / "configs"
    configs_dir.mkdir(parents=True, exist_ok=True)
    config_filename = os.path.basename(target_config_path)
    
    matches = list(repo_path.rglob(target_config_path)) or list(repo_path.rglob(config_filename))
    if matches:
        shutil.copy2(matches[0], configs_dir / config_filename)
        logger.info(f"✅ Staged unified configuration artifact: {config_filename}")
    else:
        logger.error(f"❌ CRITICAL: Configuration baseline tracking asset path '{target_config_path}' missing.")
        sys.exit(1)
    
    # 5. Serialize Pristine Sovereign State Map File
    state_container = TunerState(
        pipeline_id=task_data["pipeline_id"],
        steps=task_data.get("steps", {}),
        task_details=sorted(execution_chain, key=lambda x: x.get("order", 0)), 
        successful_runs_archive=f"successful_runs_{branch_name}",
        failed_runs_archive=f"failed_runs_{branch_name}"
    )
    
    target_state_json = workspace_dir / "state.json"
    state_container.save_to_disk(str(target_state_json))
    logger.info(f"✅ SUCCESS: Workspace layout ready. State saved to: {target_state_json}")

if __name__ == "__main__":  # pragma: no cover
    main()