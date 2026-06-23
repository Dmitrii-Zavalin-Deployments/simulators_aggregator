# src/pipeline/initialize_state.py
import os
import sys
import json
import shutil
import logging
import argparse
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
    """Scans the local 'tasks/' directory to locate and validate a task JSON."""
    tasks_dir = Path("tasks")
    logger.info(f"Scanning {tasks_dir} for an ACE execution task payload...")
    
    # Required keys according to tuner_task_schema.json
    required_keys = {"pipeline_id", "config_ids", "input_data_list"}
    
    task_files = list(tasks_dir.glob("*.json"))
    
    if not task_files:
        raise FileNotFoundError("❌ CRITICAL: No JSON files found in tasks/ directory.")

    # Validate the first found task file (or implement loop logic to select)
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

def stage_dependency_files(repo_path: Path, workspace_dir: Path, file_names: list, category: str):
    """Locates and stages required files from the repo into the workspace."""
    staging_target = workspace_dir / category
    staging_target.mkdir(parents=True, exist_ok=True)
    
    for target_name in file_names:
        file_found = False
        base_name = target_name.split('.')[0]
        
        for root, _, files in os.walk(repo_path):
            for f in files:
                if f == target_name or f.startswith(base_name):
                    source_file = Path(root) / f
                    shutil.copy2(source_file, staging_target / f)
                    logger.info(f"   ↳ Staged {category[:-1]}: {f} -> {category}/")
                    file_found = True
                    break
            if file_found:
                break
        
        if not file_found:
            logger.warning(f"⚠️ Variable tracking notice: Asset '{target_name}' not found. Creating placeholder.")
            with open(staging_target / f"{target_name}.json", 'w') as placeholder:
                json.dump({"id": target_name, "status": "placeholder"}, placeholder)

def main():
    args = parse_arguments()
    repo_path = Path(args.repo_path)
    
    if not repo_path.exists():
        logger.error(f"Provided repository path does not exist: {repo_path}")
        sys.exit(1)
        
    # 1. Resolve Environment Parameters
    branch_name = os.environ.get("GITHUB_REF_NAME", "default_branch")
    logger.info(f"Initializing state machine environment for isolation branch: [{branch_name}]")
    
    # 2. Discover and Validate Task Schema (Now targeting tasks/ directory)
    try:
        task_data = discover_task_file()
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)
        
    # 3. Create Clean-Room Isolated Workspace Sandbox Structures
    base_output_dir = Path("data/testing-input-output")
    workspace_dir = base_output_dir / f"tuning_{branch_name}"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    # 4. Execute Defensive Staging (Isolate files from repo)
    logger.info("Starting structural environment staging...")
    stage_dependency_files(repo_path, workspace_dir, task_data["config_ids"], "configs")
    stage_dependency_files(repo_path, workspace_dir, task_data["input_data_list"], "inputs")
    
    # 5. Dynamically Generate the Search-Space Super-Matrix
    logger.info("Compiling hyperparameter execution super-matrix search space...")
    combinations_to_test = []
    for config_id in task_data["config_ids"]:
        for input_data in task_data["input_data_list"]:
            combinations_to_test.append({
                "config_id": config_id,
                "input_data": input_data,
                "status": "pending",
                "execution_summary": {}
            })
    logger.info(f"Matrix built. Total distinct experimental permutations: {len(combinations_to_test)}")

    # 6. Instantiate Sovereign State Container
    try:
        state_container = TunerState(
            pipeline_id=task_data["pipeline_id"],
            config_ids=task_data["config_ids"],
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
        
        # 7. Serialize State Document
        target_state_json = workspace_dir / "state.json"
        state_container.save_to_disk(str(target_state_json))
        logger.info(f"✅ SUCCESS: Cold start completed. Sovereign state written to: {target_state_json}")
        
    except Exception as e:
        logger.error(f"❌ Structural state packaging failure: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()