#!/usr/bin/env python3
# src/pipeline/provision_environment.py

import json
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("EnvironmentProvisioner")

def main():
    root_task = Path("task.json")
    if not root_task.exists():
        logger.error("❌ CRITICAL: No task.json found at the workspace root.")
        sys.exit(1)

    # 1. Parse targets from task.json
    with open(root_task, 'r') as f:
        try:
            task_data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"❌ CRITICAL: task.json contains invalid JSON: {e}")
            sys.exit(1)

    repo_url = task_data.get("library_repository_url")
    version_tag = task_data.get("version_tag")
    pipeline_id = task_data.get("pipeline_id")

    if not all([repo_url, version_tag, pipeline_id]):
        logger.error("❌ CRITICAL: Missing vital metadata (library_repository_url, version_tag, pipeline_id) in task.json.")
        sys.exit(1)

    # 2. Clone the Payload Library
    repo_path = Path("repositories/payload_library")
    logger.info(f"🗂️ Cloning Payload Library ({version_tag}) from {repo_url}...")
    
    if repo_path.exists():
        subprocess.run(["rm", "-rf", str(repo_path)], check=True)
    
    repo_path.parent.mkdir(parents=True, exist_ok=True)
    
    clone_cmd = ["git", "clone", "--depth", "1", "--branch", version_tag, repo_url, str(repo_path)]
    result = subprocess.run(clone_cmd)
    if result.returncode != 0 or not (repo_path / ".git").exists():
        logger.error("❌ CRITICAL: Payload repository clone failed.")
        sys.exit(1)
    logger.info("✅ Payload repository cloned and staged successfully.")

    # 3. Discover Library Manifest
    search_pattern = f"{pipeline_id}*"
    manifest_matches = list(repo_path.rglob(search_pattern))
    
    if not manifest_matches:
        logger.error(f"❌ CRITICAL: Manifest targeting '{search_pattern}' could not be found in library.")
        sys.exit(1)
        
    with open(manifest_matches[0], 'r') as f:
        manifest_data = json.load(f)

    global_setup_script = manifest_data.get("setup_script")

    # 4. Execute Dynamic Downstream Setup Provisioning Script
    if global_setup_script:
        full_script_path = repo_path / global_setup_script
        print(f"::group::⚙ Provisioning Environment via Manifest: {global_setup_script}")
        logger.info(f"⚙ Executing script: {full_script_path}")
        
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
                logger.error(f"❌ CRITICAL: Manifest provisioning script failed with exit code {return_code}")
                sys.exit(return_code)
            
            logger.info("    ↳ Dynamic environment provisioning completed successfully.")
        finally:
            print("::endgroup::")
    else:
        logger.warning("⚠️ Warning: No explicit 'setup_script' entry discovered inside manifest header.")

if __name__ == "__main__":  # pragma: no cover
    main()