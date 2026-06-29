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
    """Scans the local 'tasks/' directory to locate and validate a lean task JSON."""
    tasks_dir = Path("tasks")
    logger.info(f"Scanning {tasks_dir} for an ACE execution task payload...")
    
    # Required keys according to the Tuner Task Schema (Intent only)
    required_keys = {"pipeline_id", "input_data_list"}
    
    task_files = list(tasks_dir.glob("*.json"))
    
    if not task_files:
        raise FileNotFoundError("❌ CRITICAL: No JSON files found in tasks/ directory.")

    for task_file in task_files:
        with open(task_file, 'r') as f:
            try:
                data = json.load(f)
                if required_keys.issubset(data.keys()):
                    logger.info(f"✅ Explicit task payload validated at: {task_file}")
                    return data
            except json.JSONDecodeError:
                continue
    raise ValueError("❌ CRITICAL: No JSON matching Tuner Task Schema found.")


def fetch_inputs_from_dropbox(input_data_list: list, target_dir: Path):
    """
    Input synchronization verification layer.
    Iterates through the input_data_list and verifies that each authentic asset 
    is physically present in the target directory. Raises a hard error if missing.
    """
    logger.info("Verifying integrity and presence of required input data assets...")
    target_dir.mkdir(parents=True, exist_ok=True)
    for filename in input_data_list:
        target_path = target_dir / filename
        
        if not target_path.exists():
            raise FileNotFoundError(
                f"❌ CRITICAL: Required input asset '{filename}' is missing from the target environment workspace: {target_dir}"
            )
            
        logger.info(f"   ↳ [Verified] Authentic input asset present: {filename}")


def load_pipeline_manifest(repo_path: Path, pipeline_id: str) -> list:
    """Finds and parses the target JSON manifest recursively within the Library."""
    # Added wildcard matching here to allow catching files with suffixes/extensions (e.g., 'test_pid.json')
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
        data = json.load(f)
        
    logger.info(f"✅ Discovered Library Manifest at: {manifest_matches[0]}")
    return data


def execute_setup_script(repo_path: Path, script_path: str):
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
        
    # 2. Create Clean-Room Isolated Workspace
    workspace_dir = Path("data/testing-input-output") / f"tuning_{branch_name}"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir = workspace_dir / "inputs-outputs"
    
    # 3. Verify Inputs are Present (Deterministic Asset Validation)
    try:
        fetch_inputs_from_dropbox(task_data["input_data_list"], inputs_dir)
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)
        
    # 4. Discover Library Manifest & Extract Configurations
    manifest_steps = load_pipeline_manifest(repo_path, task_data["pipeline_id"])
    
    target_config_path = None
    
    # 5. Process Manifest Steps (Conditional Setup Scripts & Config Key Capture)
    for step in sorted(manifest_steps, key=lambda x: x.get("order", 0)):
        logger.info(f"Processing Step {step.get('order')} for repository: {step.get('repository_url')}")
        
        # Execute provisioning ONLY if dependencies are NOT cached
        if "setup_script" in step:
            if not args.cached_dependency:
                execute_setup_script(repo_path, step["setup_script"])
            else:
                logger.info(f"⏩ Skipping provisioning script (Cache Hit: True): {step['setup_script']}")
            
        # Capture the unified config file location
        if "config" in step:
            target_config_path = step["config"]
            
    # 6. Stage Unified Config to Workspace (Deterministic Direct Copy)
    if target_config_path:
        configs_dir = workspace_dir / "configs"
        configs_dir.mkdir(parents=True, exist_ok=True)
        config_filename = os.path.basename(target_config_path)
        
        # Look for the exact path match first, then fall back to basename rglob if structures drift
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
    
    # 7. Instantiate Sovereign State Container
    try:
        state_container = TunerState(
            pipeline_id=task_data["pipeline_id"],
            input_data_list=task_data["input_data_list"],
            task_details=manifest_steps, 
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