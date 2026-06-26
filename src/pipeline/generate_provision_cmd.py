#!/usr/bin/env python3
import json
import os
import sys
import argparse

def main():
    # Setup argument parsing
    parser = argparse.ArgumentParser(description="Generate repository provisioning commands")
    parser.add_argument("--state-file", required=True, help="Path to the state.json file")
    args = parser.parse_args()

    # Validate state file existence
    if not os.path.exists(args.state_file):
        print(f"echo '❌ ERROR: State file {args.state_file} not located.'; exit 1")
        sys.exit(1)

    # Determine base directory and normalize to absolute path
    base_dir = os.path.dirname(os.path.abspath(args.state_file))
    
    # --------------------------------------------------------------------------
    # MATRIX QUEUE PROCESSING PHASE (Direct Python Mutation)
    # --------------------------------------------------------------------------
    combinations_path = os.path.join(base_dir, "config_combinations_array.json")
    
    if not os.path.exists(combinations_path):
        print(f"echo '❌ ERROR: Matrix file missing at {combinations_path}'; exit 1")
        sys.exit(1)

    with open(combinations_path, "r") as f:
        combinations = json.load(f)

    if not combinations or not isinstance(combinations, list) or len(combinations) == 0:
        print(f"echo '❌ ERROR: No remaining unrolled configurations available in {combinations_path}.'; exit 1")
        sys.exit(1)

    # Pop the first flat runtime configuration dict
    current_runtime_config = combinations.pop(0)

    # Write the specific isolated combination to a temporary workspace file
    config_temp_dir = os.path.join(base_dir, "config")
    os.makedirs(config_temp_dir, exist_ok=True)
    config_temp_path = os.path.join(config_temp_dir, "config_temp.json")

    with open(config_temp_path, "w") as f:
        json.dump(current_runtime_config, f, indent=4)

    # Overwrite the remaining combinations back to the array matrix
    with open(combinations_path, "w") as f:
        json.dump(combinations, f, indent=4)

    # Store the absolute path to point to during deployment execution
    abs_config_temp = os.path.abspath(config_temp_path)

    # --------------------------------------------------------------------------
    # SHELL COMMAND BUILDING PHASE
    # --------------------------------------------------------------------------
    with open(args.state_file, "r") as f:
        data = json.load(f)

    tasks = sorted(data.get("task_details", []), key=lambda x: x.get("order", 1))
    
    repo_root = "data/testing-input-output/repositories"
    commands = [f"mkdir -p {repo_root}"]
    staged_configs = []

    for task in tasks:
        repo_url = task["repository_url"]
        
        # Defensive HTTPS conversion
        if repo_url.startswith("git@github.com:"):
            repo_url = repo_url.replace("git@github.com:", "https://github.com/")
        
        version_tag = task["version_tag"]
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        repo_dir = f"{repo_root}/{repo_name}"
        
        target_config_json = f"{repo_dir}/config/config.json"
        staged_configs.append(target_config_json)

        # Using subshell execution encapsulation (cd ...) to avoid manual path traps
        cmd = (
            f"echo '📥 Cloning target simulator repository: {repo_name}...'; "
            f"if [ -d '{repo_dir}' ]; then rm -rf '{repo_dir}'; fi; "
            f"git clone {repo_url} {repo_dir} && "
            f"(cd {repo_dir} && "
            f"git checkout {version_tag} && "
            f"mkdir -p config && "
            f"cp '{abs_config_temp}' config/config.json && "
            f"echo '✅ Staged unrolled configuration successfully inside {repo_name}.')"
        )
        commands.append(cmd)

    # --------------------------------------------------------------------------
    # CONFIGURATION INTEGRITY VALIDATION & CLEANUP LOOP
    # --------------------------------------------------------------------------
    verify_script = (
        f"echo '🔍 --- COMMENCING RUNTIME CONFIGURATION INTEGRITY AUDIT ---'; "
        f"INTEGRITY_PASSED=true; "
    )
    
    for config_path in staged_configs:
        verify_script += (
            f"echo '📋 Testing content equivalence: config_temp.json ➡️ {config_path}...'; "
            f"if diff '{abs_config_temp}' '{config_path}' > /dev/null 2>&1; then "
            f"  echo '  ✅ Content match confirmed.'; "
            f"else "
            f"  echo '  ❌ CRITICAL ERROR: File content mismatch or missing asset detected!'; "
            f"  INTEGRITY_PASSED=false; "
            f"fi; "
        )
        
    verify_script += (
        f"if [ \"$INTEGRITY_PASSED\" = true ]; then "
        f"  echo '🎉 All simulator environments matched config_temp.json identically. Purging temporary asset...'; "
        f"  rm -f '{abs_config_temp}'; "
        f"else "
        f"  echo '❌ CRITICAL: Verification phase found corrupted stages. Retaining config_temp.json for analysis.'; "
        f"  exit 1; "
        f"fi"
    )
    commands.append(verify_script)

    # Output chained execution commands for runner evaluation
    print(" && ".join(commands))

if __name__ == "__main__":
    main()