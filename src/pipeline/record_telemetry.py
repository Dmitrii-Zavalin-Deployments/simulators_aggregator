import argparse
import datetime
import json
import logging
import os
import sys

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

    logger.info("========================================================================")
    logger.info("🚀 Starting telemetry capture process")
    logger.info(f"   Inputs -> --state-file: {args.state_file} | --exit-code: {args.exit_code} | --log-file: {args.log_file}")
    logger.info("========================================================================")

    # Resolve context paths
    base_dir = os.path.dirname(os.path.abspath(args.state_file))
    logger.info(f"🔍 Resolved system base_dir: {base_dir}")
    
    config_temp_path = os.path.join(base_dir, "configs", "config_temp.json")
    logger.info(f"🔍 Target config path expected by engine: {config_temp_path}")

    # Comprehensive structural pre-flight diagnostic scan
    configs_parent_dir = os.path.join(base_dir, "configs")
    if os.path.exists(configs_parent_dir):
        logger.info(f"📂 Found 'configs' directory. Listing contents: {os.listdir(configs_parent_dir)}")
    else:
        logger.warning(f"❌ Physical 'configs' directory does not exist at: {configs_parent_dir}")

    # Handle dormant state
    logger.info(f"⚙️ Checking for existence of staging asset: {config_temp_path}")
    if not os.path.exists(config_temp_path):
        logger.error(f"❌ CRITICAL: Verification failed: {config_temp_path} is missing.")
        logger.error("📋 Notice: Temporary execution configuration file not found. Telemetry mapping aborted.")
        logger.error("🚫 Terminating processing stream with escalation status 1.")
        sys.exit(1)

    # 1. Read configuration
    logger.info(f"📖 Reading configuration contents from staging file: {config_temp_path}")
    with open(config_temp_path, "r") as f:
        config_content = f.read()
    logger.info(f"✅ Configuration data ingested successfully ({len(config_content)} characters).")

    # 2. Determine execution state
    status = "success" if args.exit_code == 0 else "failed"
    logger.info(f"📊 Evaluated simulator outcome status: {status.upper()}")

    # 3. Capture logs on failure
    error_log = None
    if status == "failed":
        logger.info(f"🔎 Status is FAILED. Investigating simulation log file at: {args.log_file}")
        if os.path.exists(args.log_file):
            with open(args.log_file, "r") as f:
                error_log = f.read()
            logger.warning(f"⚠️ Simulation failure logs ingested successfully ({len(error_log)} characters).")
        else:
            logger.error(f"❌ Environmental Mismatch: Simulation failed but log file not found at: {args.log_file}")

    # 4. Build telemetry object
    logger.info("🏗️ Assembling structured telemetry JSON schema payload...")
    telemetry_data = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Tuner Results Schema",
        "config": json.loads(config_content),
        "status": status,
        "error_log": error_log
    }

    # 5. Write output
    target_archive = "successful_runs_archive" if status == "success" else "failed_runs_archive"
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_context_dir = os.path.join(base_dir, target_archive, f"run_{timestamp}")
    
    logger.info(f"📂 Allocating physical destination workspace: {run_context_dir}")
    os.makedirs(run_context_dir, exist_ok=True)
    logger.info("✅ Workspace directory verified/created.")
    
    output_path = os.path.join(run_context_dir, "telemetry_results.json")
    logger.info(f"✍️ Writing payload compilation to final storage target: {output_path}")

    with open(output_path, "w") as f:
        json.dump(telemetry_data, f, indent=4)
    logger.info(f"✅ Telemetry record successfully generated: {output_path}")

    # 6. Housekeeping
    logger.info("🧹 Commencing workspace cleanup tasks...")
    if os.path.exists(config_temp_path):
        os.remove(config_temp_path)
        logger.info(f"🗑️ Purged staging asset from system: {config_temp_path}")

    # 7. Final status
    if status == "failed":
        logger.error("🚫 Terminating processing stream with escalation status 1.")
        sys.exit(1)
    
    logger.info("🎉 Telemetry pipeline execution cycle finished nominally. Exiting with status 0.")
    sys.exit(0)

if __name__ == "__main__":  # pragma: no cover
    main()