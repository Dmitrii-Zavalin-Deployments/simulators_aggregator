import os
import sys
import json
import shutil
import logging
import argparse
import subprocess
from pathlib import Path
from src.state.tuner_state import TunerState

# Configure explicit logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("StateInitializer")


def parse_arguments():
    parser = argparse.ArgumentParser(description="ACE Loop Cold Start State Initializer")
    # Support both options seamlessly mapping to repo_path
    parser.add_argument("--repository-path", "--repo-path", required=True, dest="repo_path", help="Path to the repository")
    return parser.parse_args()


def discover_task_file() -> dict:
    """
    Locates and validates the pipeline execution task payload.
    Checks for task.json at the workspace root first, then falls back to the tasks/ directory.
    """
    # Check if task.json exists at root level first
    root_task = Path("task.json")
    if root_task.exists():
        logger.info(f"✅ Discovered baseline task payload at workspace root: {root_task}")
        task_file = root_task
    else:
        raise FileNotFoundError("❌ CRITICAL: No task.json at root")

    with open(task_file, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"❌ CRITICAL: Task file {task_file.name} contains invalid JSON: {e}")
            
    if not isinstance(data, dict):
        raise ValueError(f"❌ CRITICAL: Task file {task_file.name} root element must be a JSON object.")
        
    logger.info(f"✅ Explicit task payload validated at: {task_file}")
    return data


def load_pipeline_manifest(repo_path: Path, pipeline_id: str) -> dict:
    """Finds and parses the target JSON manifest recursively within the Library."""
    search_pattern = f"{pipeline_id}*"
    manifest_matches = list(repo_path.rglob(search_pattern))
    
    if not manifest_matches:
        error_msg = (
            f"\n{'='*80}\n"
            f"🚨 CRITICAL: Manifest '{search_pattern}' could not be found.\n"
            f"💡 HINT: Confirm the 'pipeline_id' maps cleanly to the file listed inside the library repository.\n"
            f"{'='*80}"
        )
        logger.error(error_msg)
        sys.stderr.flush()
        raise FileNotFoundError(f"Manifest '{search_pattern}' not found in {repo_path}")
        
    with open(manifest_matches[0], 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"❌ CRITICAL: Manifest file {manifest_matches[0].name} contains invalid JSON: {e}")
            
    if not isinstance(data, dict):
        raise ValueError(f"❌ CRITICAL: Manifest file {manifest_matches[0].name} root element must be a JSON object.")
        
    logger.info(f"✅ Discovered Library Manifest at: {manifest_matches[0]}")
    return data


def execute_setup_script(repo_path: Path, script_path: str):
    """Executes the downstream repository initialization script to provision environment modules."""
    full_script_path = repo_path / script_path
    print(f"::group::⚙ Provisioning: {script_path}")
    logger.info(f"⚙ Executing provisioning script: {script_path}")
    
    try:
        process = subprocess.Popen(
            ["bash", str(full_script_path.resolve())],
            cwd=str(repo_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in process.stdout:
            print(f"    [Bash]: {line.strip()}")
            
        return_code = process.wait()
        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, "Provisioning script failed")
        
        logger.info("    ↳ Provisioning completed successfully.")
        
    finally:
        print("::endgroup::")


def fetch_inputs_from_dropbox(steps: dict):
    """Input synchronization layer. Gathers assets into workspace folders."""
    logger.info("Verifying integrity and presence of required step-routed remote data assets...")
    unique_folders = {Path(step_meta["input_output_folder"]) for step_meta in steps.values() if step_meta.get("input_output_folder")}
    
    if not unique_folders:
        logger.info("No input/output folders specified in steps. Skipping Dropbox synchronization.")
        return

    from src.io.dropbox_utils import TokenManager
    from src.io.download_from_dropbox import CloudIngestor
    
    # Enforce strict ingestion criteria
    app_key = os.environ.get("DROPBOX_APP_KEY")
    app_secret = os.environ.get("DROPBOX_APP_SECRET")
    refresh_token = os.environ.get("DROPBOX_REFRESH_TOKEN")
    dropbox_folder = os.environ.get("DROPBOX_FOLDER", "simulators").strip("/")
    
    if not all([app_key, app_secret, refresh_token]):
        raise EnvironmentError("❌ CRITICAL: Missing required Dropbox credentials in environment variables.")
    
    # Initialize infrastructure dependencies
    tm = TokenManager(app_key, app_secret)
    ingestor = CloudIngestor(tm, refresh_token, Path("dropbox_download.log"))
    
    # Format absolute remote directory path according to Dropbox API namespace constraints
    # (Dropbox root is an empty string "", while subfolders require a leading slash)
    remote_folder_path = f"/{dropbox_folder}" if dropbox_folder else ""
    
    # Execute deterministic batch ingestion
    for target_dir in unique_folders:
        logger.info(f"Syncing Dropbox folder '{remote_folder_path}' to '{target_dir}' via native sync engine...")
        try:
            # Passing allowed_ext=[] tells the native engine to fetch all discovered assets
            ingestor.sync(remote_folder_path, target_dir, allowed_ext=[])
        except Exception as e:
            raise FileNotFoundError(
                f"❌ CRITICAL: Ingestion engine failed to synchronize remote Dropbox path "
                f"'{remote_folder_path}' into local directory '{target_dir}'. Error: {e}"
            )

def main():
    args = parse_arguments()
    repo_path = Path(args.repo_path)
    
    if not repo_path.exists():
        logger.error(f"Provided repository path does not exist: {repo_path}")
        sys.exit(1)
        
    branch_name = os.environ.get("GITHUB_REF_NAME", "default_branch")
    logger.info(f"Initializing state engine for branch: [{branch_name}] (Deterministic Cold Start Run)")
    
    # 1. Discover Task Schema
    try:
        task_data = discover_task_file()
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)
        
    # 2. Discover Library Manifest
    try:
        manifest_data = load_pipeline_manifest(repo_path, task_data["pipeline_id"])
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)
        
    target_config_path = manifest_data.get("config")
    global_setup_script = manifest_data.get("setup_script")
    execution_chain = manifest_data.get("execution_chain", [])
    
    # 3. DETERMINISTIC RE-PROVISIONING: Global setup execution runs every time
    if global_setup_script:
        execute_setup_script(repo_path, global_setup_script)
    else:
        logger.warning("⚠️ Warning: No explicit 'setup_script' entry discovered inside manifest header.")

    for step in sorted(execution_chain, key=lambda x: x.get("order", 0)):
        logger.info(f"Scheduled Execution Sequence -> Step {step.get('order')} Target: {step.get('repository_url')}")

    # 4. Create Workspace Structure
    workspace_dir = Path("data/testing-input-output") / f"tuning_{branch_name}"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    # 5. Hydrate Inputs
    try:
        # Check if "steps" exists in root task payload, fallback to structured steps map gracefully
        steps_payload = task_data.get("steps", {})
        fetch_inputs_from_dropbox(steps_payload)
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)
            
    # 6. Stage Unified Config Blueprint
    if target_config_path:
        configs_dir = workspace_dir / "configs"
        configs_dir.mkdir(parents=True, exist_ok=True)
        config_filename = os.path.basename(target_config_path)
        
        matches = list(repo_path.rglob(target_config_path))
        if not matches:
            matches = list(repo_path.rglob(config_filename))
            
        if matches:
            shutil.copy2(matches[0], configs_dir / config_filename)
            logger.info(f"✅ Staged unified configuration artifact: {config_filename}")
        else:
            logger.error(f"❌ CRITICAL: Configuration baseline tracking asset path '{target_config_path}' could not be resolved.")
            sys.exit(1)
    else:
        logger.error("❌ CRITICAL: Manifest configuration validation failed. Root layout requires a baseline configuration parameter.")
        sys.exit(1)
    
    # 7. Serialize Pristine Sovereign State Map File
    try:
        state_container = TunerState(
            pipeline_id=task_data["pipeline_id"],
            steps=task_data.get("steps", {}),
            task_details=sorted(execution_chain, key=lambda x: x.get("order", 0)), 
            successful_runs_archive=f"successful_runs_{branch_name}",
            failed_runs_archive=f"failed_runs_{branch_name}"
        )
        
        target_state_json = workspace_dir / "state.json"
        state_container.save_to_disk(str(target_state_json))
        logger.info(f"✅ SUCCESS: Cold start sequence terminated cleanly. State serialized to: {target_state_json}")
        
    except Exception as e:
        logger.error(f"❌ Structural state packaging execution failure: {e}")
        sys.exit(1)

if __name__ == "__main__":  # pragma: no cover
    main()