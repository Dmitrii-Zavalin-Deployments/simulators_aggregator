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

    if not os.path.exists(args.state_file):
        print(f"echo '❌ ERROR: State file {args.state_file} not located.'; exit 1")
        sys.exit(1)

    # Determine base directory (e.g., data/testing-input-output/tuning_main)
    base_dir = os.path.dirname(args.state_file)

    with open(args.state_file, "r") as f:
        data = json.load(f)

    tasks = sorted(data.get("task_details", []), key=lambda x: x.get("order", 1))
    
    commands = ["mkdir -p repositories"]

    for task in tasks:
        repo_url = task["repository_url"]
        
        # Defensive HTTPS conversion
        if repo_url.startswith("git@github.com:"):
            repo_url = repo_url.replace("git@github.com:", "https://github.com/")
        
        version_tag = task["version_tag"]
        config_source = task["config"] 

        repo_name = repo_url.split("/")[-1].replace(".git", "")
        repo_dir = f"repositories/{repo_name}"
        
        # Dynamically map the config file to the directory of the state file
        config_filename = os.path.basename(config_source)
        source_config_asset = os.path.join(base_dir, "configs", config_filename)

        cmd = (
            f"echo '📥 Cloning target: {repo_name}...'; "
            f"if [ -d '{repo_dir}' ]; then rm -rf '{repo_dir}'; fi; "
            f"git clone {repo_url} {repo_dir}; "
            f"cd {repo_dir}; "
            f"git checkout {version_tag}; "
            f"mkdir -p config; "
            f"cp {source_config_asset} config/config.json; "
            f"cd ../..; "
            f"echo '✅ Staged {repo_name} successfully.'"
        )
        commands.append(cmd)

    print(" && ".join(commands))

if __name__ == "__main__":
    main()