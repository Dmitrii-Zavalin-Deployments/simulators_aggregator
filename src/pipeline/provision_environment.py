import os
import sys
import json
import logging
import argparse
import subprocess
from pathlib import Path

# Configure explicit logging for system tracing
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PROVISION] [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("EnvironmentProvisioner")

def parse_arguments():
    parser = argparse.ArgumentParser(description="ACE Loop Environment Provisioning Engine")
    parser.add_argument("--repo-path", required=True, help="Path to the library repository")
    return parser.parse_args()

def discover_task_file() -> dict:
    """Scans local workspace tasks to discover target intent parameters."""
    tasks_dir = Path("tasks")
    required_keys = {"pipeline_id", "input_data_list"}
    task_files = list(tasks_dir.glob("*.json"))
    
    if not task_files:
        raise FileNotFoundError("❌ CRITICAL: No execution payload found in tasks/.")

    for task_file in task_files:
        with open(task_file, 'r') as f:
            try:
                data = json.load(f)
                if required_keys.issubset(data.keys()):
                    return data
            except json.JSONDecodeError:
                continue
    raise ValueError("❌ CRITICAL: No structural JSON matches Tuner Task Schema.")

def load_pipeline_manifest(repo_path: Path, pipeline_id: str) -> list:
    """Locates the manifest document inside the staged repository."""
    search_pattern = f"{pipeline_id}.json"
    manifest_matches = list(repo_path.rglob(search_pattern))
    
    if not manifest_matches:
        raise FileNotFoundError(f"Manifest configuration asset '{search_pattern}' not found in {repo_path}")
        
    with open(manifest_matches[0], 'r') as f:
        return json.load(f)

def execute_setup_script(repo_path: Path, script_path: str):
    """Executes the setup script directly into the currently active shell environment."""
    full_script_path = repo_path / script_path
    print(f"::group::📦 Provisioning Conda Environment via: {script_path}")
    logger.info(f"Executing step provisioning shell driver: {script_path}")
    
    try:
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
            raise subprocess.CalledProcessError(return_code, "Library environment provisioning failed.")
        
        logger.info("   ↳ Environment step completed successfully.")
    finally:
        print("::endgroup::")

def main():
    args = parse_arguments()
    repo_path = Path(args.repo_path)
    
    if not repo_path.exists():
        logger.error(f"Target repository mirror path does not exist: {repo_path}")
        sys.exit(1)
        
    try:
        task_data = discover_task_file()
        manifest_steps = load_pipeline_manifest(repo_path, task_data["pipeline_id"])
        
        logger.info("Parsing pipeline steps to extract target environment shell drivers...")
        for step in sorted(manifest_steps, key=lambda x: x.get("order", 0)):
            if "setup_script" in step:
                execute_setup_script(repo_path, step["setup_script"])
                
        logger.info("✅ SUCCESS: Conda environment population completed without exceptions.")
    except Exception as e:
        logger.error(f"❌ Environment provisioning phase broken: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()