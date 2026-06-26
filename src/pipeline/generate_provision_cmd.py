#!/usr/bin/env python3
import json
import os
import sys

def main():
    state_file = "data/testing-input-output/tuning_main/state.json"
    
    if not os.path.exists(state_file):
        print("echo '❌ ERROR: State file state.json not located.'; exit 1")
        return

    with open(state_file, "r") as f:
        data = json.load(f)

    # Sort tasks sequentially by execution order contract
    tasks = sorted(data.get("task_details", []), key=lambda x: x.get("order", 1))
    
    commands = []
    commands.append("mkdir -p repositories")

    for task in tasks:
        repo_url = task["repository_url"]  # Kept raw (e.g., git@github.com:...)
        version_tag = task["version_tag"]
        config_source = task["config"] 

        # Scrape and isolate the repo folder name dynamically from the git URL
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        repo_dir = f"repositories/{repo_name}"
        
        # Cleanly resolve configuration filename mapping to its source asset folder
        config_filename = os.path.basename(config_source)
        source_config_asset = f"data/testing-input-output/tuning_main/configs/{config_filename}"

        # Construct the execution command sequence string
        cmd = (
            f"echo '📥 Executing clone for target: {repo_name}...'; "
            f"if [ -d '{repo_dir}' ]; then rm -rf '{repo_dir}'; fi; "
            f"git clone {repo_url} {repo_dir}; "
            f"cd {repo_dir}; "
            f"git checkout {version_tag}; "
            f"mkdir -p config; "
            f"cp ../../{source_config_asset} config/config.json; "
            f"cd ../..; "
            f"echo '✅ Staging transaction complete for: {repo_name}'"
        )
        commands.append(cmd)

    # Output the unified single string shell execution command
    print(" && ".join(commands))

if __name__ == "__main__":
    main()