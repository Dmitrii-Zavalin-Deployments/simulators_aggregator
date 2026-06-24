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
    parser.add_argument("--repo-path", required=True, help="Path to the repository")
    return parser.parse_args()

def discover_task_file() -> dict:
    """Scans the local 'tasks/' directory to locate and validate a lean task JSON."""
    tasks_dir = Path("tasks")
    logger.info(f"Scanning {tasks_dir} for an ACE execution task payload...")
    
    # Required keys according to the NEW Tuner Task Schema (Intent only)
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
    Simulated Dropbox integration layer.
    Iterates through the input_data_list and downloads them to the target_dir.
    """
    logger.info("Initiating Dropbox synchronization for input data...")
    target_dir.mkdir(parents=True, exist_ok=True)
    for filename in input_data_list:
        target_path = target_dir / filename
        logger.info(f"   ↳ Downloading: {filename}")
        with open(target_path, 'w') as f:
            f.write("Mock CAD/Step Data")

def load_pipeline_manifest(repo_path: Path, pipeline_id: str) -> list:
    """Finds and parses the target JSON manifest recursively within the Library."""
    
    # We look for the base name. 
    # Note: If the file was renamed with a hash, this pattern match will fail, 
    # which is exactly what triggers the diagnostic logic below.
    manifest_matches = list(repo_path.rglob(pipeline_id))
    
    if not manifest_matches:
        error_msg = (
            f"\n{'='*80}\n"
            f"🚨 CRITICAL: Manifest '{search_pattern}' could not be found.\n"
            f"💡 HINT: Files in the Library Repository have been version-locked.\n"
            "   It is highly likely this file was renamed (e.g., added a git-hash suffix).\n"
            "   1. Check the 'pipelines/' folder in your 'fluid_dynamics_simulator' repo.\n"
            "   2. Identify the new filename (e.g., 'mesh_pipeline_<hash>.json').\n"
            "   3. Update your task file in 'tasks/' to point to the new filename.\n"
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
    print(f"::group::⚙️ Provisioning: {script_path}")
    logger.info(f"⚙️ Executing provisioning script: {script_path}")
    
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
            print(f"   [Bash]: {line.strip()}")
            
        return_code = process.wait()
        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, "Provisioning script failed")
        
        logger.info("   ↳ Provisioning completed successfully.")
        
    finally:
        print("::endgroup::")

def stage_dependency_files(repo_path: Path, workspace_dir: Path, config_ids: list, subfolder: str):
    """Recursively locates config assets and stages them into the workspace."""
    target_dir = workspace_dir / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)
    for config_id in config_ids:
        matches = list(repo_path.rglob(config_id))
        if matches:
            shutil.copy2(matches[0], target_dir / filename)
            logger.info(f"✅ Successfully staged asset: {filename}")
        else:
            logger.warning(f"⚠️ Asset '{config_id}' not found.")

def main():
    args = parse_arguments()
    repo_path = Path(args.repo_path)
    
    if not repo_path.exists():
        logger.error(f"Provided repository path does not exist: {repo_path}")
        sys.exit(1)
        
    branch_name = os.environ.get("GITHUB_REF_NAME", "default_branch")
    logger.info(f"Initializing state machine for branch: [{branch_name}]")
    
    # 1. Discover Task Schema
    try:
        task_data = discover_task_file()
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)
        
    # 2. Create Clean-Room Isolated Workspace
    workspace_dir = Path("data/testing-input-output") / f"tuning_{branch_name}"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir = workspace_dir / "inputs"
    
    # 3. Download Inputs from Dropbox
    fetch_inputs_from_dropbox(task_data["input_data_list"], inputs_dir)
    
    # 4. Discover Library Manifest & Extract Configurations
    manifest_steps = load_pipeline_manifest(repo_path, task_data["pipeline_id"])
    
    all_config_ids = []
    
    # 5. Process Manifest Steps (Setup Scripts & Config Extraction)
    for step in sorted(manifest_steps, key=lambda x: x.get("order", 0)):
        logger.info(f"Processing Step {step.get('order')} for repository: {step.get('repository_url')}")
        
        # Execute provisioning
        if "setup_script" in step:
            execute_setup_script(repo_path, step["setup_script"])
            
        # Aggregate configs
        if "config_ids" in step:
            all_config_ids.extend(step["config_ids"])
            
    # Remove duplicates if any configs overlap between steps
    unique_config_ids = list(set(all_config_ids))
    
    # 6. Stage Configs to Workspace
    stage_dependency_files(repo_path, workspace_dir, unique_config_ids, "configs")
    
    # 7. Dynamically Generate the Search-Space Super-Matrix
    logger.info("Compiling hyperparameter execution super-matrix search space...")
    combinations_to_test = []
    for config_id in unique_config_ids:
        for input_file in task_data["input_data_list"]:
            combinations_to_test.append({
                "config_id": config_id,
                "input_data": str(inputs_dir / input_file), # Explicit path resolving to the downloaded file
                "status": "pending",
                "execution_summary": {}
            })
            
    logger.info(f"Matrix built. Total distinct experimental permutations: {len(combinations_to_test)}")

    # 8. Instantiate Sovereign State Container
    try:
        state_container = TunerState(
            pipeline_id=task_data["pipeline_id"],
            input_data_list=task_data["input_data_list"],
            successful_runs_archive=f"successful_runs_{branch_name}.zip",
            failed_runs_archive=f"failed_runs_{branch_name}.zip",
            saap_skeleton=f"saap_skeleton_{branch_name}",
            saap_skeleton_path=str(workspace_dir / "saap_skeleton"),
            success_zip_path=str(workspace_dir / f"successful_runs_{branch_name}.zip"),
            failed_zip_path=str(workspace_dir / f"failed_zip_{branch_name}.zip"),
            combinations_to_test=combinations_to_test,
            successful_runs=[],
            failed_runs=[],
            batch_cursor=0
        )
        
        # 9. Serialize State Document
        target_state_json = workspace_dir / "state.json"
        state_container.save_to_disk(str(target_state_json))
        logger.info(f"✅ SUCCESS: Cold start completed. Sovereign state written to: {target_state_json}")
        
    except Exception as e:
        logger.error(f"❌ Structural state packaging failure: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()