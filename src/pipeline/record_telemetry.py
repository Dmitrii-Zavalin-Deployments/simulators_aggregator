#!/usr/bin/env python3
import json
import os
import sys
import argparse
import datetime

def main():
    parser = argparse.ArgumentParser(description="Record matrix simulation telemetry and handle workspace cleanup")
    parser.add_argument("--state-file", required=True, help="Path to the state.json file")
    parser.add_argument("--exit-code", type=int, required=True, help="The exit code from the simulator run step")
    parser.add_argument("--log-file", required=True, help="Path to the captured log file containing console output")
    args = parser.parse_args()

    # Resolve context paths relative to state file location
    base_dir = os.path.dirname(os.path.abspath(args.state_file))
    config_temp_path = os.path.join(base_dir, "config", "config_temp.json")
    successful_runs_dir = os.path.join(base_dir, "successful_runs")

    # Handle case where the pipeline is dormant (config_temp.json was never generated)
    if not os.path.exists(config_temp_path):
        print("📋 Notice: No temporary config file found. Skipping telemetry mapping (Dormant state).")
        sys.exit(0)

    # 1. Read the exact configuration content utilized during this specific execution run
    with open(config_temp_path, "r") as f:
        config_content = f.read()

    # 2. Determine execution state mapping
    status = "success" if args.exit_code == 0 else "failed"

    # 3. Capture logs if standard run encountered an issue
    error_log = None
    if status == "failed" and os.path.exists(args.log_file):
        with open(args.log_file, "r") as f:
            error_log = f.read()

    # 4. Build data object matching the requested schema exactly
    telemetry_data = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Tuner Results Schema",
        "config": config_content,
        "status": status,
        "error_log": error_log
    }

    # 5. Ensure output directory exists and write timestamped JSON file
    os.makedirs(successful_runs_dir, exist_ok=True)
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_filename = f"run_{timestamp}_{status}.json"
    output_path = os.path.join(successful_runs_dir, output_filename)

    with open(output_path, "w") as f:
        json.dump(telemetry_data, f, indent=4)
    print(f"✅ Telemetry record successfully generated: {output_path}")

    # 6. Housekeeping: Purge configuration staging file from workspace
    if os.path.exists(config_temp_path):
        os.remove(config_temp_path)
        print("🗑️ Cleaned up workspace: Staging asset 'config_temp.json' removed.")

    # 7. Propagate failure code back to GitHub Actions runner if simulation failed
    if status == "failed":
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()