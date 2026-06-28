#!/usr/bin/env python3
import json
import os
import sys
import argparse
import datetime
import logging

# Configure logging for GitHub Actions console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("TelemetryRecorder")

def main():
    parser = argparse.ArgumentParser(description="Record matrix simulation telemetry and handle workspace cleanup")
    parser.add_argument("--state-file", required=True, help="Path to the state.json file")
    parser.add_argument("--exit-code", type=int, required=True, help="The exit code from the simulator run step")
    parser.add_argument("--log-file", required=True, help="Path to the captured log file")
    args = parser.parse_args()

    logger.info(f"🚀 Starting telemetry capture for state file: {args.state_file}")

    # Resolve context paths
    base_dir = os.path.dirname(os.path.abspath(args.state_file))
    config_temp_path = os.path.join(base_dir, "config", "config_temp.json")
    successful_runs_dir = os.path.join(base_dir, "successful_runs")

    # Handle dormant state
    if not os.path.exists(config_temp_path):
        logger.info("📋 Notice: No temporary config file found. Skipping telemetry mapping (Dormant state).")
        sys.exit(0)

    # 1. Read configuration
    with open(config_temp_path, "r") as f:
        config_content = f.read()

    # 2. Determine execution state
    status = "success" if args.exit_code == 0 else "failed"
    logger.info(f"📊 Execution status: {status.upper()}")

    # 3. Capture logs on failure
    error_log = None
    if status == "failed":
        if os.path.exists(args.log_file):
            with open(args.log_file, "r") as f:
                error_log = f.read()
            logger.warning("⚠️ Simulation failed. Error logs captured.")
        else:
            logger.error(f"❌ Simulation failed but log file not found at: {args.log_file}")

    # 4. Build telemetry object
    telemetry_data = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Tuner Results Schema",
        "config": config_content,
        "status": status,
        "error_log": error_log
    }

    # 5. Write output
    os.makedirs(successful_runs_dir, exist_ok=True)
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_filename = f"run_{timestamp}_{status}.json"
    output_path = os.path.join(successful_runs_dir, output_filename)

    with open(output_path, "w") as f:
        json.dump(telemetry_data, f, indent=4)
    logger.info(f"✅ Telemetry record successfully generated: {output_path}")

    # 6. Housekeeping
    if os.path.exists(config_temp_path):
        os.remove(config_temp_path)
        logger.info("🗑️ Cleaned up workspace: Staging asset 'config_temp.json' removed.")

    # 7. Final status
    if status == "failed":
        logger.error("🚫 Exiting with error status 1.")
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":  # pragma: no cover
    main()