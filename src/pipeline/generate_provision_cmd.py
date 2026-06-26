#!/usr/bin/env python3
import json
import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Generate repository provisioning commands")
    parser.add_argument("--state-file", required=True, help="Path to the state.json file")
    parser.add_argument("--cached-dependency", action="store_true", help="Pass cache hit flag to initializers")
    args = parser.parse_args()

    if not os.path.exists(args.state_file):
        print(f"echo '❌ ERROR: State file {args.state_file} not located.'; exit 1")
        sys.exit(1)

    base_dir = os.path.dirname(os.path.abspath(args.state_file))
    combinations_path = os.path.join(base_dir, "config_combinations_array.json")
    
    if not os.path.exists(combinations_path):
        print(f"echo '❌ ERROR: Matrix file missing at {combinations_path}'; exit 1")
        sys.exit(1)

    with open(combinations_path, "r") as f:
        combinations = json.load(f)

    if not combinations or not isinstance(combinations, list) or len(combinations) == 0:
        print(f"echo '❌ ERROR: No remaining unrolled configurations available.'; exit 1")
        sys.exit(1)

    # 🎯 KEY REQUIREMENT STEP: Pop exactly ONE variant for ALL repositories
    current_runtime_config = combinations.pop(0)

    # Save this single source of truth temporarily
    config_temp_dir = os.path.join(base_dir, "config")
    os.makedirs(config_temp_dir, exist_ok=True)
    config_temp_path = os.path.join(config_temp_dir, "config_temp.json")

    with open(config_temp_path, "w") as f:
        json.dump(current_runtime_config, f, indent=4)

    # Save the remaining matrix variations back to disk
    with open(combinations_path, "w") as f:
        json.dump(combinations, f, indent=4)

    abs_config_temp = os.path.abspath(config_temp_path)

    # Load targets from state file
    with open(args.state_file, "r") as f:
        data = json.load(f)

    tasks = sorted(data.get("task_details", []), key=lambda x: x.get("order", 1))
    repo_root = "data/testing-input-output/repositories"
    commands = [f"mkdir -p {repo_root}"]
    staged_configs = []
    
    cached_flag = "--cached-dependency" if args.cached_dependency else ""

    # Loop through all folders and inject the identical config asset
    for task in tasks:
        repo_url = task["repository_url"]
        if repo_url.startswith("git@github.com:"):
            repo_url = repo_url.replace("git@github.com:", "https://github.com/")
        
        version_tag = task["version_tag"]
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        repo_dir = f"{repo_root}/{repo_name}"
        
        target_config_json = f"{repo_dir}/config/config.json"
        staged_configs.append(target_config_json)

        # Inject the single config source of truth into this specific simulator
        cmd = (
            f"echo '📥 Cloning target simulator repository: {repo_name}...'; "
            f"if [ -d '{repo_dir}' ]; then rm -rf '{repo_dir}'; fi; "
            f"git clone {repo_url} {repo_dir} && "
            f"(cd {repo_dir} && "
            f"  git checkout {version_tag} && "
            f"  mkdir -p config && "
            f"  cp '{abs_config_temp}' config/config.json && "
            f"  echo '✅ Staged identical configuration variant inside {repo_name}.') && "
            f"echo '⚙️ Running state initialization logic for {repo_name}...' && "
            f"python3 src/pipeline/initialize_state.py --repo-path '{repo_dir}' {cached_flag}"
        )
        commands.append(cmd)

    # 🔬 Strict Integrity Check: Verify that ALL injected files are exactly identical
    verify_script = (
        f"echo '🔍 --- COMMENCING TARGET VARIANT INTEGRITY AUDIT ---'; "
        f"INTEGRITY_PASSED=true; "
    )
    for config_path in staged_configs:
        verify_script += (
            f"if diff '{abs_config_temp}' '{config_path}' > /dev/null 2>&1; then "
            f"  echo '  ✅ Verification Passed: {config_path} matches source.'; "
            f"else "
            f"  echo '  ❌ CRITICAL INTEGRITY MISMATCH DETECTED AT: {config_path}'; "
            f"  INTEGRITY_PASSED=false; "
            f"fi; "
        )
        
    verify_script += (
        f"if [ \"$INTEGRITY_PASSED\" = true ]; then "
        f"  echo '🎉 Success: All configurations successfully matched. Purging temp artifact.'; "
        f"  rm -f '{abs_config_temp}'; "
        f"else "
        f"  echo '❌ CRITICAL: Pipeline variation validation failed.'; "
        f"  exit 1; "
        f"fi"
    )
    commands.append(verify_script)

    print(" && ".join(commands))

if __name__ == "__main__":
    main()