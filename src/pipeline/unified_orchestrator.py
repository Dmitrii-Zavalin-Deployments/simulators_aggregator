#!/usr/bin/env python3
# src/pipeline/unified_orchestrator.py

import json
import os
import sys
import argparse
import logging
import subprocess
from pathlib import Path

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger("UnifiedOrchestrator")

def main():
    logger = setup_logging()
    
    parser = argparse.ArgumentParser(description="Unified ACE Loop Workspace Provisioner and Chain Executor")
    parser.add_argument("--state-file", required=True, help="Path to the state.json file")
    parser.add_argument("--log-file", required=True, help="Path where simulator execution logs will be written")
    args = parser.parse_args()

    # 1. Dormant State Pre-flight Check
    dormant_flag_path = "dormant.flag"
    if os.path.exists(dormant_flag_path):
        with open(dormant_flag_path, "r") as f:
            content = f.read().strip()
        if "STATUS: DORMANT" in content:
            logger.info("🏁 Pipeline status is DORMANT. Matrix options exhausted.")
            sys.exit(0)

    # 2. State & Matrix Validation
    state_path = Path(args.state_file)
    if not state_path.exists():
        logger.error(f"❌ CRITICAL: Execution state file missing at {state_path}")
        sys.exit(1)

    base_dir = state_path.parent
    combinations_path = base_dir / "config_combinations_array.json"
    
    if not combinations_path.exists():
        logger.error(f"❌ CRITICAL: Matrix definition file missing at {combinations_path}")
        sys.exit(1)

    with open(combinations_path, "r") as f:
        combinations = json.load(f)

    if not combinations or not isinstance(combinations, list) or len(combinations) == 0:
        logger.warning("🏁 All configuration variations have been completely exhausted.")
        with open(dormant_flag_path, "w") as f:
            f.write("STATUS: DORMANT\n")
        sys.exit(0)

    # 3. Pop Active Runtime Configuration Combination Slice
    current_runtime_config = combinations.pop(0)
    logger.info(f"📦 Popped next variation matrix target configuration. Remaining: {len(combinations)}")

    # Stage config_temp.json where telemetry engine explicitly expects it
    configs_dir = base_dir / "configs"
    configs_dir.mkdir(parents=True, exist_ok=True)
    config_temp_path = configs_dir / "config_temp.json"

    with open(config_temp_path, "w") as f:
        json.dump(current_runtime_config, f, indent=4)

    # Write the remaining matrix array entries back to disk
    with open(combinations_path, "w") as f:
        json.dump(combinations, f, indent=4)

    # 4. Load Pipeline Step Map Specifications
    with open(state_path, "r") as f:
        state_data = json.load(f)

    steps = state_data.get("steps", {})
    tasks = sorted(state_data.get("task_details", []), key=lambda x: x.get("order", 0))
    repo_root = Path("data/testing-input-output/repositories")
    repo_root.mkdir(parents=True, exist_ok=True)

    # Ensure log file workspace is cleared out before starting execution stream
    log_file_path = Path(args.log_file)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    if log_file_path.exists():
        os.remove(log_file_path)

    # 5. Iterative Provision-and-Execute Loop Flow
    for step_id, step_meta in sorted(steps.items(), key=lambda x: int(x[0])):
        step_idx = int(step_id)
        task = next((t for t in tasks if t.get("order") == step_idx), None)
        if not task and len(tasks) >= step_idx:
            task = tasks[step_idx - 1]
            
        if not task:
            logger.warning(f"⚠️ Step {step_id} has no matching task metadata layout configured.")
            continue

        repo_url = task["repository_url"].replace("git@github.com:", "https://github.com/")
        version_tag = task["version_tag"]
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        repo_dir = repo_root / repo_name

        logger.info(f"⚙️ Processing Execution Chain Step [{step_id}] -> Repository: {repo_name}")

        # A. Provision Stage (Clone + Checkout + Inject Config)
        if repo_dir.exists():
            subprocess.run(["rm", "-rf", str(repo_dir)], check=True)
        
        logger.info(f"  📥 Cloning {repo_url} at tag {version_tag}...")
        subprocess.run(["git", "clone", repo_url, str(repo_dir)], check=True)
        subprocess.run(["git", "checkout", version_tag], cwd=str(repo_dir), check=True)

        # Inject popped configuration variant profile directly into module layout root
        module_config_dir = repo_dir / "config"
        module_config_dir.mkdir(parents=True, exist_ok=True)
        shutil_config_target = module_config_dir / "config.json"
        
        with open(shutil_config_target, "w") as f:
            json.dump(current_runtime_config, f, indent=4)

        # B. Execute Simulation Stage
        # Dynamically locate the precise subfolder inside our branch workspace holding the assets
        dropbox_sync_dir = base_dir / "input-output"
        in_file = step_meta.get("input_file_name", "")
        out_file = step_meta.get("output_file_name", "")

        logger.info(f"  🚀 Executing Simulation Engine for step {step_id}...")
        
        # Build command sequence
        run_cmd = [
            "xvfb-run", "--auto-servernum", 
            "python3", "-m", "src.main",
            "--input_output_folder", str(dropbox_sync_dir.resolve()),
            "--input_file", in_file,
            "--output_file", out_file
        ]

        # Execute and append output capture telemetry streams cleanly to unified log target
        with open(log_file_path, "a") as log_out:
            log_out.write(f"\n--- STEP {step_id} LOGS ({repo_name}) ---\n")
            log_out.flush()
            
            result = subprocess.run(
                run_cmd,
                cwd=str(repo_dir),
                stdout=log_out,
                stderr=subprocess.STDOUT,
                text=True
            )

        if result.returncode != 0:
            logger.error(f"❌ CRITICAL: Step {step_id} reported execution failure (Exit Code: {result.returncode}).")
            sys.exit(result.returncode)
            
        logger.info(f"  ✅ Step {step_id} finished processing successfully.")

    logger.info("🎉 All sequence execution steps executed nominally across the pipeline graph chain.")
    sys.exit(0)

if __name__ == "__main__":  # pragma: no cover
    main()