import argparse
import json
import logging
import os
import subprocess
import sys
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
    logger.info("🎬 Orchestrator process invoked. Parsing execution environment parameters...")
    
    parser = argparse.ArgumentParser(description="Unified ACE Loop Workspace Provisioner and Chain Executor")
    parser.add_argument("--state-file", required=True, help="Path to the state.json file")
    parser.add_argument("--log-file", required=True, help="Path where simulator execution logs will be written")
    args = parser.parse_args()

    logger.info(f"📋 Received Arguments -> --state-file: {args.state_file} | --log-file: {args.log_file}")

    # 1. Dormant State Pre-flight Check
    dormant_flag_path = "dormant.flag"
    logger.info(f"🔍 Checking for presence of system dormancy flag: {dormant_flag_path}")
    if os.path.exists(dormant_flag_path):
        with open(dormant_flag_path, "r") as f:
            content = f.read().strip()
        logger.info(f"📄 Dormancy flag content read: '{content}'")
        if "STATUS: DORMANT" in content:
            logger.info("🏁 Pipeline status is DORMANT. Matrix options exhausted. Terminating loop cleanly.")
            sys.exit(0)
    else:
        logger.info("✅ No active dormancy flag detected. Proceeding to structural validations.")

    # 2. State & Matrix Validation
    state_path = Path(args.state_file)
    logger.info(f"🔍 Validating physical existence of state mapping path: {state_path.resolve()}")
    if not state_path.exists():
        logger.error(f"❌ CRITICAL: Execution state file missing at {state_path.resolve()}")
        logger.error(f"EXITING AT LINE: {__import__('inspect').currentframe().f_lineno}")
        sys.exit(1)

    base_dir = state_path.parent
    combinations_path = base_dir / "config_combinations_array.json"
    logger.info(f"🔍 Validating physical existence of configuration matrix path: {combinations_path.resolve()}")
    
    if not combinations_path.exists():
        logger.error(f"❌ CRITICAL: Matrix definition file missing at {combinations_path.resolve()}")
        logger.error(f"EXITING AT LINE: {__import__('inspect').currentframe().f_lineno}")
        sys.exit(1)

    logger.info("📖 Reading configuration array variations matrix...")
    with open(combinations_path, "r") as f:
        try:
            combinations = json.load(f)
        except Exception as e:
            logger.error(f"❌ CRITICAL: Failed to parse JSON matrix from {combinations_path}. Error: {e}")
            logger.error(f"EXITING AT LINE: {__import__('inspect').currentframe().f_lineno}")
            sys.exit(1)

    logger.info(f"📊 Configuration matrix structural analysis: Loaded type={type(combinations)}, Length={len(combinations) if isinstance(combinations, list) else 'N/A'}")

    if not combinations or not isinstance(combinations, list) or len(combinations) == 0:
        logger.warning("🏁 All configuration variations have been completely exhausted.")
        with open(dormant_flag_path, "w") as f:
            f.write("STATUS: DORMANT\n")
        sys.exit(0)

    # 3. Pop Active Runtime Configuration Combination Slice
    current_runtime_config = combinations.pop(0)
    logger.info(f"📦 Popped next variation matrix target configuration. Remaining items in pool: {len(combinations)}")
    logger.info(f"⚙️ Active variation slice signature: {json.dumps(current_runtime_config)[:120]}...")

    # Stage config_temp.json where telemetry engine explicitly expects it
    configs_dir = base_dir / "configs"
    logger.info(f"📁 Ensuring staging infrastructure directory exists: {configs_dir.resolve()}")
    configs_dir.mkdir(parents=True, exist_ok=True)
    config_temp_path = configs_dir / "config_temp.json"

    logger.info(f"✍️ Staging dynamic runtime execution configuration asset profile to: {config_temp_path.resolve()}")
    with open(config_temp_path, "w") as f:
        json.dump(current_runtime_config, f, indent=4)

    logger.info("✍️ Writing updated residual matrix array variant pool back to storage disk...")
    with open(combinations_path, "w") as f:
        json.dump(combinations, f, indent=4)

    # 4. Load Pipeline Specifications
    logger.info(f"📖 Loading pipeline architectural map rules from sovereign state file: {state_path.resolve()}")
    with open(state_path, "r") as f:
        try:
            state_data = json.load(f)
        except Exception as e:
            logger.error(f"❌ CRITICAL: Failed to parse state JSON structure. Error: {e}")
            logger.error(f"EXITING AT LINE: {__import__('inspect').currentframe().f_lineno}")
            sys.exit(1)

    logger.info("🔍 --- SOVEREIGN STATE MAP DIAGNOSTIC PRINT ---")
    logger.info(f"📄 Full State Keys Discovered: {list(state_data.keys())}")
    
    if "task_details" not in state_data:
        logger.error("❌ CRITICAL: Key 'task_details' is completely absent from state.json.")
        logger.error(f"EXITING AT LINE: {__import__('inspect').currentframe().f_lineno}")
        sys.exit(1)
        
    tasks = state_data["task_details"]
    logger.info(f"📋 'task_details' field inspection: type={type(tasks)}, count={len(tasks) if isinstance(tasks, list) else 'N/A'}")
    
    if not isinstance(tasks, list) or not tasks:
        logger.error("❌ DIAGNOSTIC ALERT: The 'task_details' list is EMPTY or structurally malformed. Loop cannot execute!")
        logger.error(f"EXITING AT LINE: {__import__('inspect').currentframe().f_lineno}")
        sys.exit(1)
        
    # --- NO-DEFAULT POLICY VALIDATION LAYER ---
    logger.info("🛡️ Performing strict structural validation check over task properties...")
    for idx, task in enumerate(tasks):
        if not isinstance(task, dict):
            logger.error(f"❌ CRITICAL: Task configuration item at list index [{idx}] is not a valid JSON object structure.")
            logger.error(f"EXITING AT LINE: {__import__('inspect').currentframe().f_lineno}")
            sys.exit(1)
        if "order" not in task or task["order"] is None:
            logger.error(f"❌ CRITICAL: Element property 'order' is missing or unassigned at list index [{idx}].")
            logger.error(f"EXITING AT LINE: {__import__('inspect').currentframe().f_lineno}")
            sys.exit(1)
        if "repository_url" not in task or not str(task["repository_url"]).strip():
            logger.error(f"❌ CRITICAL: Required property 'repository_url' is missing or blank at list index [{idx}].")
            logger.error(f"EXITING AT LINE: {__import__('inspect').currentframe().f_lineno}")
            sys.exit(1)
        if "version_tag" not in task or not str(task["version_tag"]).strip():
            logger.error(f"❌ CRITICAL: Required property 'version_tag' is missing or blank at list index [{idx}].")
            logger.error(f"EXITING AT LINE: {__import__('inspect').currentframe().f_lineno}")
            sys.exit(1)
        if "input_file_name" not in task or not str(task["input_file_name"]).strip():
            logger.error(f"❌ CRITICAL: Required property 'input_file_name' is missing or blank at list index [{idx}].")
            logger.error(f"EXITING AT LINE: {__import__('inspect').currentframe().f_lineno}")
            sys.exit(1)
        if "output_file_name" not in task or not str(task["output_file_name"]).strip():
            logger.error(f"❌ CRITICAL: Required property 'output_file_name' is missing or blank at list index [{idx}].")
            logger.error(f"EXITING AT LINE: {__import__('inspect').currentframe().f_lineno}")
            sys.exit(1)
    
    try:
        tasks = sorted(tasks, key=lambda x: int(x["order"]))
    except Exception as e:
        logger.error(f"⚠️ Failed to sort task data array items by order parameter value. Error: {e}")
        logger.error(f"EXITING AT LINE: {__import__('inspect').currentframe().f_lineno}")
        sys.exit(1)

    repo_root = Path("data/testing-input-output/repositories")
    logger.info(f"📁 Allocating system workspace storage root framework at: {repo_root.resolve()}")
    repo_root.mkdir(parents=True, exist_ok=True)

    # Ensure log file workspace is cleared out before starting execution stream
    log_file_path = Path(args.log_file)
    logger.info(f"📝 Configuring destination processing trace log target location: {log_file_path.resolve()}")
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    if log_file_path.exists():
        logger.info("🧹 Pre-existing run trace file detected. Cleaving log asset target space...")
        os.remove(log_file_path)

    # 5. Iterative Provision-and-Execute Loop Flow (Direct Pipeline Loop)
    logger.info(f"🚀 Found {len(tasks)} pipeline execution sequences scheduled inside task profiles.")

    for task in tasks:
        # Assured strict direct dictionary lookups with no fallbacks
        step_id = str(task["order"])
        repo_url = task["repository_url"].replace("git@github.com:", "https://github.com/")
        version_tag = task["version_tag"]
        in_file = task["input_file_name"]
        out_file = task["output_file_name"]

        repo_name = repo_url.split("/")[-1].replace(".git", "")
        repo_dir = repo_root / repo_name

        logger.info(f"⚙️ Processing Execution Chain Task [{step_id}] -> Repository: {repo_name} | Target Directory: {repo_dir.resolve()}")

        # A. Provision Stage (Clone + Checkout + Inject Config)
        if repo_dir.exists():
            logger.info(f"🧹 Stale execution repository tracking path found at '{repo_dir}'. Evicting file paths...")
            subprocess.run(["rm", "-rf", str(repo_dir)], check=True)
        
        logger.info(f"  📥 Cloning {repo_url} at tag version context {version_tag}...")
        subprocess.run(["git", "clone", repo_url, str(repo_dir)], check=True)
        logger.info(f"  🔀 Checking out code version context at deployment marker branch: {version_tag}")
        subprocess.run(["git", "checkout", version_tag], cwd=str(repo_dir), check=True)

        # Inject popped configuration variant profile directly into module layout root
        module_config_dir = repo_dir / "config"
        logger.info(f"  📁 Generating environment config tracking layout targets inside target repo: {module_config_dir.resolve()}")
        module_config_dir.mkdir(parents=True, exist_ok=True)
        shutil_config_target = module_config_dir / "config.json"
        
        logger.info(f"  ✍️ Injecting active dynamic matrix runtime validation profile straight into module workspace: {shutil_config_target}")
        with open(shutil_config_target, "w") as f:
            json.dump(current_runtime_config, f, indent=4)

        # B. Execute Simulation Stage
        dropbox_sync_dir = base_dir / "input-output"

        logger.info(f"  🚀 Building execution environment commands for task step {step_id}...")
        logger.info(f"  📂 Expected internal Dropbox context workspace folder path: {dropbox_sync_dir.resolve()}")
        logger.info(f"  📥 In-file asset parameter target: '{in_file}' | Out-file target: '{out_file}'")
        
        # Build command sequence
        run_cmd = [
            "xvfb-run", "--auto-servernum", 
            "python3", "-m", "src.main",
            "--input_output_folder", str(dropbox_sync_dir.resolve()),
            "--input_file", in_file,
            "--output_file", out_file
        ]

        logger.info(f"  🎬 Dispatched command string sequence: {' '.join(run_cmd)}")
        
        # Execute and append output capture telemetry streams cleanly to unified log target
        with open(log_file_path, "a") as log_out:
            log_out.write(f"\n--- TASK STEP {step_id} LOGS ({repo_name}) ---\n")
            log_out.flush()
            
            result = subprocess.run(
                run_cmd,
                cwd=str(repo_dir),
                stdout=log_out,
                stderr=subprocess.STDOUT,
                text=True
            )

        logger.info(f"  📉 Execution phase for task finished tracking. Process exit status return code: {result.returncode}")

        if result.returncode != 0:
            logger.error(f"❌ CRITICAL: Task Step {step_id} reported execution failure (Exit Code: {result.returncode}).")
            sys.exit(result.returncode)
            
        logger.info(f"  ✅ Task Step {step_id} finished processing successfully.")

    logger.info("🎉 All sequence execution tasks executed nominally across the pipeline graph chain.")
    sys.exit(0)

if __name__ == "__main__":  # pragma: no cover
    main()