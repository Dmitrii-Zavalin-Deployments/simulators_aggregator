import json
import os
import sys
import argparse
import logging

def setup_logging():
    """Configures the logger to output to stderr."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s',
        stream=sys.stderr
    )
    return logging.getLogger("pipeline_generator")

def main():
    # logger initialized inside main to ensure capture by pytest fixtures
    logger = setup_logging() 

    parser = argparse.ArgumentParser(description="Generate repository execution commands")
    parser.add_argument("--state-file", required=True, help="Path to the state.json file")
    args = parser.parse_args()

    # 🛑 CASE 1: Check Dormant Flag
    dormant_flag_path = "dormant.flag"
    if os.path.exists(dormant_flag_path):
        with open(dormant_flag_path, "r") as f:
            content = f.read().strip()
        
        if "STATUS: DORMANT" in content:
            logger.info("Pipeline state is DORMANT. Exhausting configuration chain.")
            shutdown_commands = [
                "echo '🏁 Notice: All configuration variations have been completely exhausted.'",
                "echo 'STATUS: DORMANT' > dormant.flag",
                "echo '✅ Successfully set pipeline state to DORMANT inside dormant.flag.'"
            ]
            print(" && ".join(shutdown_commands))
            sys.exit(0)

    # 🚀 CASE 2: Pipeline is ACTIVE
    if not os.path.exists(args.state_file):
        logger.error(f"Execution state file '{args.state_file}' not located.")
        print(f"echo '❌ ERROR: Execution state file {args.state_file} not located.'; exit 1")
        sys.exit(1)

    logger.info(f"Processing state file: {args.state_file}")
    
    base_dir = os.path.dirname(os.path.abspath(args.state_file))
    inputs_outputs_dir = os.path.join(base_dir, "inputs-outputs")

    with open(args.state_file, "r") as f:
        data = json.load(f)

    tasks = sorted(data.get("task_details", []), key=lambda x: x.get("order", 1))
    repo_root = "data/testing-input-output/repositories"
    
    commands = []
    for task in tasks:
        repo_url = task["repository_url"]
        if repo_url.startswith("git@github.com:"):
            repo_url = repo_url.replace("git@github.com:", "https://github.com/")
        
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        repo_dir = f"{repo_root}/{repo_name}"
        
        logger.info(f"Adding task for repository: {repo_name}")
        cmd = (
            f"echo '🚀 Running simulator engine execution block: {repo_name}...'; "
            f"(cd {repo_dir} && python3 -m src.main --input_output_folder {inputs_outputs_dir})"
        )
        commands.append(cmd)

    if not commands:
        logger.warning("Active state detected, but no task profiles were configured.")
        print("echo '📋 Notice: Active state detected, but no task profiles were configured in state.json.'")
        sys.exit(0)

    print(" && ".join(commands))

if __name__ == "__main__":
    main()