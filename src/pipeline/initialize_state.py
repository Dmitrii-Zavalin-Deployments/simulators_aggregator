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

# Configure explicit logging for pipeline execution visibility
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("StateInitializer")

def parse_arguments():
    parser = argparse.ArgumentParser(description="ACE Loop Cold Start State Initializer")
    parser.add_argument(
        "--repo-path", 
        required=True, 
        help="Path to the cloned simulator library repository"
    )
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
                        
    raise ValueError("❌ CRITICAL: No JSON matching Tuner Task Schema found in tasks/ directory.")

def fetch_inputs_from_dropbox(input_data_list: list, target_dir: Path):
    """
    Simulated Dropbox integration layer.
    Iterates through the input_data_list and downloads them to the target_dir.
    """
    logger.info("Initiating Dropbox synchronization for input data...")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    for filename in input_data_list:
        target_path = target_dir / filename
        logger.info(f"   ↳ Downloading from Dropbox: {filename} -> {target_path}")
        # TODO: Insert actual Dropbox API SDK logic here:
        # dropbox_client.files_download_to_file(str(target_path), f"/SaaP_Inputs/{filename}")
        
        # Mocking file creation for structural integrity
        with open(target_path, 'w') as f:
            f.write("Mock CAD/Step Data")

def load_pipeline_manifest(repo_path: Path, pipeline_id: str) -> list:
    """Finds and parses the target JSON manifest recursively within the Library."""
    # Use rglob to search recursively for the manifest file anywhere in the repo
    search_pattern = f"{pipeline_id}.json"
    manifest_matches = list(repo_path.rglob(search_pattern))
    
    if not manifest_matches:
        # If we can't find it, we print a directory tree snippet to help you debug the next time
        dir_content = [str(x.relative_to(repo_path)) for x in repo_path.rglob("*.json")]
        raise FileNotFoundError(
            f"❌ CRITICAL: Manifest '{search_pattern}' not found in library at {repo_path}.\n"
            f"Available JSON files found: {dir_content}"
        )
    
    # Use the first match found
    manifest_path = manifest_matches[0]
    
    with open(manifest_path, 'r') as f:
        manifest_data = json.load(f)
        
    logger.info(f"✅ Discovered Library Manifest at: {manifest_path}")
    return manifest_data

def execute_setup_script(repo_path: Path, script_path: str):
    """Runs the environment provisioning script defined in the library manifest."""
    full_script_path = repo_path / script_path
    
    if not full_script_path.exists():
        logger.warning(f"⚠️ Setup script not found at {full_script_path}. Skipping.")
        return

    logger.info(f"⚙️ Executing provisioning script: {script_path}")
    try:
        # Execute script with the repo_path as the working directory
        subprocess.run(
            ["bash", str(full_script_path)], 
            cwd=str(repo_path), 
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("   ↳ Provisioning completed successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Provisioning script failed!\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")
        raise

def stage_dependency_files(repo_path: Path, workspace_dir: Path, file_names: list, category: str):
    """Locates and stages required files from the repo into the workspace."""
    staging_target = workspace_dir / category
    staging_target.mkdir(parents=True, exist_ok=True)
    
    for target_name in file_names:
        file_found = False
        for root, _, files in os.walk(repo_path):
            if target_name in files:
                source_file = Path(root) / target_name
                shutil.copy2(source_file, staging_target / target_name)
                logger.info(f"   ↳ Staged {category[:-1]}: {target_name} -> {category}/")
                file_found = True
                break
        
        if not file_found:
            logger.warning(f"⚠️ Asset '{target_name}' not found in repo.")

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