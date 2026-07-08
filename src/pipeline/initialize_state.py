# src/pipeline/initialize_state.py
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
    # Idiomatic boolean flag: True if present, False if absent
    parser.add_argument("--cached-dependency", action="store_true", help="Flag indicating environment/conda cache hit achieved; skips provisioning scripts")
    return parser.parse_args()


def discover_task_file() -> dict:
    """
    Scans the local 'tasks/' directory to locate and validate a single lean task JSON.
    Enforces that exactly one task context exists.
    """
    tasks_dir = Path("tasks")
    logger.info(f"Scanning {tasks_dir} for an ACE execution task payload...")
    
    # Required keys according to the Tuner Task Schema
    required_keys = {"pipeline_id", "input_data_list"}
    
    task_files = list(tasks_dir.glob("*.json"))
    
    # Guard 1: Zero files presence
    if not task_files:
        raise FileNotFoundError("❌ CRITICAL: No JSON files found in tasks/ directory.")

    # Guard 2: More than 1 file presence (Ambiguous state prevention)
    if len(task_files) > 1:
        found_names = [f.name for f in task_files]
        raise ValueError(
            f"❌ CRITICAL: Multiple task files found in tasks/ directory: {found_names}. "
            f"Only exactly ONE task file is allowed at a time. Please delete additional files."
        )
    
    task_file = task_files[0]
    with open(task_file, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"❌ CRITICAL: Task file {task_file.name} contains invalid JSON: {e}")
            
    # Enforce strict object type assignment matching the schema root
    if not isinstance(data, dict):
        raise ValueError(f"❌ CRITICAL: Task file {task_file.name} root element must be a JSON object, not a list.")
        
    if not required_keys.issubset(data.keys()):
        raise ValueError(f"❌ CRITICAL: JSON file '{task_file.name}' is missing required schema keys: {required_keys - data.keys()}")
        
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
            f"💡 HINT: Files in the Library Repository have been version-locked.\n"
            f"   It is highly likely this file was renamed (e.g., added a git-hash suffix).\n"
            f"   1. Check the 'pipelines/' folder in your 'fluid_dynamics_simulator' repo.\n"
            f"   2. Identify the new filename (e.g., 'mesh_pipeline_<hash>.json').\n"
            f"   3. Update your task file in 'tasks/' to point to the new filename.\n"
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
        # Popen streams logs in real-time
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


def fetch_inputs_from_dropbox(input_data_list: list, target_dir: Path):
    """
    Input synchronization layer.
    Guaranteed to run post-provisioning. Safely pulls down assets using dynamic 
    lazy imports that resolve cleanly now that dependencies are present.
    """
    logger.info("Verifying integrity and presence of required input data assets...")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    ingestor = None
    
    for filename in input_data_list:
        target_path = target_dir / filename
        logger.info(f"DEBUG: Checking for asset at path: {target_path.resolve()}")
        
        if not target_path.exists():
            logger.info(f"⚠ Asset '{filename}' is missing locally. Initiating direct Dropbox download...")
            
            # Lazily initialize Dropbox modules. Safely evaluates since setup scripts have completed.
            if ingestor is None:
                from src.io.dropbox_utils import TokenManager
                from src.io.download_from_dropbox import CloudIngestor
                
                app_key = os.environ.get("DROPBOX_APP_KEY")
                app_secret = os.environ.get("DROPBOX_APP_SECRET")
                refresh_token = os.environ.get("DROPBOX_REFRESH_TOKEN")
                dropbox_folder = os.environ.get("DROPBOX_FOLDER", "simulators").strip("/")
                
                if not all([app_key, app_secret, refresh_token]):
                    raise EnvironmentError(
                        "❌ CRITICAL: Missing required Dropbox credentials (DROPBOX_APP_KEY, "
                        "DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN) in environment."
                    )
                
                tm = TokenManager(app_key, app_secret)
                ingestor = CloudIngestor(tm, refresh_token, target_dir.parent / "dropbox_download.log")
            
            remote_path = f"/{dropbox_folder}/{filename}"
            try:
                ingestor.download_file(remote_path, target_path)
            except Exception as e:
                raise FileNotFoundError(
                    f"❌ CRITICAL: Failed to download asset '{filename}' from Dropbox path '{remote_path}'. Error: {e}"
                )
                
        logger.info(f"   ↳ [Verified] Authentic input asset present: {filename}")


def main():
    args = parse_arguments()
    repo_path = Path(args.repo_path)
    
    if not repo_path.exists():
        logger.error(f"Provided repository path does not exist: {repo_path}")
        sys.exit(1)
        
    branch_name = os.environ.get("GITHUB_REF_NAME", "default_branch")
    logger.info(f"Initializing state machine for branch: [{branch_name}] (Conda Cache Hit: {args.cached_dependency})")
    
    # 1. Discover Task Schema
    try:
        task_data = discover_task_file()
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)
        
    # 2. Discover Library Manifest (Resolves to Object Root Contract)
    try:
        manifest_data = load_pipeline_manifest(repo_path, task_data["pipeline_id"])
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)
        
    # Extract Global Configuration Properties from Header
    target_config_path = manifest_data.get("config")
    global_setup_script = manifest_data.get("setup_script")
    execution_chain = manifest_data.get("execution_chain", [])
    
    # 3. CRITICAL ENVIRONMENT HYDRATION: Run Global Setup Script
    if global_setup_script:
        if not args.cached_dependency:
            execute_setup_script(repo_path, global_setup_script)
        else:
            logger.info(f"⏩ Skipping global provisioning script (Cache Hit: True): {global_setup_script}")
    else:
        logger.warning("⚠️ Warning: No unified 'setup_script' entry found in manifest root header.")

    # Print planned tracking metrics for logging transparency
    for step in sorted(execution_chain, key=lambda x: x.get("order", 0)):
        logger.info(f"Scheduled Execution Sequence -> Step {step.get('order')} Target: {step.get('repository_url')}")

    # 4. Create Clean-Room Isolated Workspace Structures
    workspace_dir = Path("data/testing-input-output") / f"tuning_{branch_name}"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir = workspace_dir / "inputs-outputs"
    
    # 5. Verify Inputs are Present (Fully insulated against missing dependency exceptions)
    try:
        fetch_inputs_from_dropbox(task_data["input_data_list"], inputs_dir)
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)
            
    # 6. Stage Unified Config to Workspace (Deterministic Direct Copy)
    if target_config_path:
        configs_dir = workspace_dir / "configs"
        configs_dir.mkdir(parents=True, exist_ok=True)
        config_filename = os.path.basename(target_config_path)
        
        # Look for the exact path match first, then fall back to rglob if structures drift
        matches = list(repo_path.rglob(target_config_path))
        if not matches:
            matches = list(repo_path.rglob(config_filename))
            
        if matches:
            shutil.copy2(matches[0], configs_dir / config_filename)
            logger.info(f"✅ Successfully staged unified config asset: {config_filename}")
        else:
            logger.error(f"❌ CRITICAL: Configuration file '{target_config_path}' could not be located inside {repo_path}")
            sys.exit(1)
    else:
        logger.error("❌ CRITICAL: Manifest schema violation. No 'config' baseline file specified.")
        sys.exit(1)
    
    # 7. Instantiate Sovereign State Container (Propagates execution array down for command generation)
    try:
        state_container = TunerState(
            pipeline_id=task_data["pipeline_id"],
            input_data_list=task_data["input_data_list"],
            task_details=sorted(execution_chain, key=lambda x: x.get("order", 0)), 
            successful_runs_archive=f"successful_runs_{branch_name}",
            failed_runs_archive=f"failed_runs_{branch_name}"
        )
        
        # 8. Serialize State Document
        target_state_json = workspace_dir / "state.json"
        state_container.save_to_disk(str(target_state_json))
        logger.info(f"✅ SUCCESS: Cold start completed. Sovereign state written to: {target_state_json}")
        
    except Exception as e:
        logger.error(f"❌ Structural state packaging failure: {e}")
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()