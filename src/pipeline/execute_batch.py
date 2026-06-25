#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import time
import uuid

def copy_artifacts(src_dir, dest_dir):
    """Copies all generated files to the execution folder, excluding .git directories."""
    if not os.path.exists(src_dir):
        return
    os.makedirs(dest_dir, exist_ok=True)
    for item in os.listdir(src_dir):
        if item == ".git":
            continue
        s = os.path.join(src_dir, item)
        d = os.path.join(dest_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks=False, ignore=shutil.ignore_patterns('.git'))
        else:
            shutil.copy2(s, d)

def main():
    parser = argparse.ArgumentParser(description="ACE Batch Execution Engine Module")
    parser.add_argument("--workspace", required=True, help="Path to active branch transaction folder")
    parser.add_argument("--batch-size", type=int, default=1, help="Number of permutations to run in this pulse")
    args = parser.parse_args()

    matrix_path = os.path.join(args.workspace, "config_combinations_array.json")
    state_path = os.path.join(args.workspace, "state.json")

    # CRITICAL: Fresh run check logic
    if not os.path.exists(matrix_path):
        print("tuning_done=true")
        return

    with open(matrix_path, "r") as f:
        queue = json.load(f)

    if not queue:
        print("tuning_done=true")
        return

    with open(state_path, "r") as f:
        state_data = json.load(f)

    # Pull configuration targets dynamically from the State passbook
    success_dir_name = state_data.get("successful_runs_archive", "successful_runs_archive")
    failed_dir_name = state_data.get("failed_runs_archive", "failed_runs_archive")

    # Pull configurations for the current batch pulse
    batch = queue[:args.batch_size]
    remaining_queue = queue[args.batch_size:]

    repo_root = "data/testing-input-output/repositories"
    os.makedirs(repo_root, exist_ok=True)
    tasks = sorted(state_data.get("task_details", []), key=lambda x: x.get("order", 1))

    for config_element in batch:
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        execution_failed = False
        captured_error = None

        # Execute pipeline modules sequentially
        for task in tasks:
            repo_url = task["repository_url"]
            repo_name = repo_url.split("/")[-1].replace(".git", "")
            target_clone_dir = os.path.join(repo_root, repo_name)

            if os.path.exists(target_clone_dir):
                subprocess.run(f"rm -rf {target_clone_dir}", shell=True, check=True)
            
            clone_res = subprocess.run(f"git clone {repo_url} {target_clone_dir}", shell=True, capture_output=True, text=True)
            if clone_res.returncode != 0:
                execution_failed = True
                captured_error = f"Git clone failed for {repo_url}: {clone_res.stderr}"
                break

            # Overwrite the target configuration with the current single-value permutation
            target_config_json = os.path.join(target_clone_dir, "config", "config.json")
            os.makedirs(os.path.dirname(target_config_json), exist_ok=True)
            with open(target_config_json, "w") as cf:
                json.dump(config_element, cf, indent=4)

            # Run primary physics/simulation solver script
            run_res = subprocess.run("python3 main.py", shell=True, cwd=target_clone_dir, capture_output=True, text=True)
            if run_res.returncode != 0:
                execution_failed = True
                captured_error = f"Execution runtime crash in {repo_name}. Stderr: {run_res.stderr}"
                break

        duration = time.time() - start_time
        
        # Set target directories dynamically based on execution outcome and state properties
        archive_folder_name = failed_dir_name if execution_failed else success_dir_name
        run_destination_path = os.path.join(args.workspace, archive_folder_name, run_id)
        os.makedirs(run_destination_path, exist_ok=True)

        result_payload = {
            "run_id": run_id,
            "status": "failed" if execution_failed else "success",
            "execution_time_seconds": round(duration, 3),
            "module_output": f"{archive_folder_name}/{run_id}",
            "error_log": captured_error,
            "configuration": config_element
        }

        # Save individual tracking metrics directly inside the unzipped isolated run directory
        with open(os.path.join(run_destination_path, "telemetry_results.json"), "w") as rf:
            json.dump(result_payload, rf, indent=4)

        if os.path.exists(repo_root):
            copy_artifacts(repo_root, os.path.join(run_destination_path, "artifacts"))

    # Atomically write back the remaining consumed queue matrix
    with open(matrix_path, "w") as f:
        json.dump(remaining_queue, f, indent=4)

    # Always output tuning_done=false when a batch completes to pass token to next schedule loop
    print("tuning_done=false")

if __name__ == "__main__":
    main()