#!/usr/bin/env python3
import json
import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Generate repository execution commands")
    parser.add_argument("--state-file", required=True, help="Path to the state.json file")
    args = parser.parse_args()

    # 🛑 CASE 1: Check Dormant Flag at the core of the repository
    dormant_flag_path = "dormant.flag"
    if os.path.exists(dormant_flag_path):
        with open(dormant_flag_path, "r") as f:
            content = f.read().strip()
        
        if "STATUS: DORMANT" in content:
            shutdown_commands = [
                "echo '🏁 Notice: All configuration variations have been completely exhausted.'",
                "echo 'STATUS: DORMANT' > dormant.flag",
                "echo '✅ Successfully set pipeline state to DORMANT inside dormant.flag.'"
            ]
            print(" && ".join(shutdown_commands))
            sys.exit(0)  # Exit cleanly so the GHA step passes but evaluates a notice chain

    # 🚀 CASE 2: Pipeline is ACTIVE -> Process State Machine Matrix Execution
    if not os.path.exists(args.state_file):
        print(f"echo '❌ ERROR: Execution state file {args.state_file} not located.'; exit 1")
        sys.exit(1)

    # Derive base path (e.g., data/testing-input-output/tuning_main)
    base_dir = os.path.dirname(os.path.abspath(args.state_file))
    inputs_outputs_dir = os.path.join(base_dir, "inputs-outputs")

    with open(args.state_file, "r") as f:
        data = json.load(f)

    # Extract tasks and sort ascending by order
    tasks = sorted(data.get("task_details", []), key=lambda x: x.get("order", 1))
    repo_root = "data/testing-input-output/repositories"
    
    commands = []

    # Loop through the ordered pipeline tasks and build execution chains
    for task in tasks:
        repo_url = task["repository_url"]
        if repo_url.startswith("git@github.com:"):
            repo_url = repo_url.replace("git@github.com:", "https://github.com/")
        
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        repo_dir = f"{repo_root}/{repo_name}"
        
        # Build the exact execution command targeting the resolved matrix directories
        cmd = (
            f"echo '🚀 Running simulator engine execution block: {repo_name}...'; "
            f"python3 {repo_dir}/src/main.py "
            f"--input_folder {inputs_outputs_dir} "
            f"--output_folder {inputs_outputs_dir}"
        )
        commands.append(cmd)

    # If the state file has no tasks listed
    if not commands:
        print("echo '📋 Notice: Active state detected, but no task profiles were configured in state.json.'")
        sys.exit(0)

    # Print the final chained execution string to standard output for eval evaluation
    print(" && ".join(commands))

if __name__ == "__main__":
    main()