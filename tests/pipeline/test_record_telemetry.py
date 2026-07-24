import json
import logging
from unittest.mock import patch

import pytest

from src.pipeline import record_telemetry

# ==============================================================================
# 1. Dormant State Verification
# ==============================================================================

# When the pipeline is triggered but the required temporary configuration is absent,
# the system is considered in a 'dormant' state. It is not a runtime failure of 
# the simulator itself, but rather a lack of work to process. 
# The system must formally exit, ensuring no orphan processes continue.

def test_main_dormant_state(tmp_path, caplog):
    # We simulate a state file path but ensure the 'configs/config_temp.json' 
    # file is physically absent from the filesystem.
    state_file = tmp_path / "state.json"
    log_file = tmp_path / "dummy.log"
    
    # We assert that the application terminates, acknowledging the missing 
    # configuration file as a termination signal.
        with caplog.at_level(logging.INFO), \
            patch("sys.argv", ["script", "--state-file", str(state_file), "--exit-code", "0", "--log-file", str(log_file)]):
        with pytest.raises(SystemExit) as exc:
            record_telemetry.main()
        assert exc.value.code == 1
    
    # Verify the specific notice was logged to the console for auditability.
    assert "Notice: Temporary execution configuration file not found" in caplog.text

# ==============================================================================
# 2. Success Path Verification
# ==============================================================================

# In the 'Happy Path', the simulator completes successfully (exit code 0).
# The system must fulfill three distinct contracts:
#     1. Ingest the temporary configuration parameters.
#     2. Generate a structured JSON telemetry artifact.
#     3. Perform atomic cleanup by purging the temporary configuration file.

def test_main_success_path(tmp_path, caplog):
    # Setup: Construct the directory structure required by the Sovereign Container:
    #     base_dir/configs/config_temp.json
    base_dir = tmp_path / "sim_run"
    config_dir = base_dir / "configs"
    config_dir.mkdir(parents=True)
    
    state_file = base_dir / "state.json"
    config_file = config_dir / "config_temp.json"
    log_file = base_dir / "execution.log"
    config_file.write_text('{"params": "test"}')
    
    # Execute the main orchestrator to finalize the state.
        with caplog.at_level(logging.INFO), \
            patch("sys.argv", ["script", "--state-file", str(state_file), "--exit-code", "0", "--log-file", str(log_file)]):
        with pytest.raises(SystemExit) as exc:
            record_telemetry.main()
        assert exc.value.code == 0
            
    # Verification of state:
    # 1. A new run record must be created within the 'successful_runs_archive'.
    runs_dir = base_dir / "successful_runs_archive"
    assert runs_dir.exists()
    assert len(list(runs_dir.glob("run_*/telemetry_results.json"))) == 1
    
    # 2. The temporary configuration file must be purged to maintain workspace hygiene.
    assert not config_file.exists()

# ==============================================================================
# 3. Failure Path Verification
# ==============================================================================

# If a simulator concludes with a failure (exit code 1), root-cause analysis 
# requires visibility into the logs. The system must capture the error log 
# contents and embed them directly into the generated telemetry JSON record.

def test_main_failure_path(tmp_path, caplog):
    # Setup: Create a filesystem environment containing an error log for ingestion.
    base_dir = tmp_path / "sim_run"
    config_dir = base_dir / "configs"
    config_dir.mkdir(parents=True)
    
    state_file = base_dir / "state.json"
    config_file = config_dir / "config_temp.json"
    log_file = base_dir / "error.log"
    
    config_file.write_text('{"params": "failure_mode"}')
    error_msg = "CRITICAL ERROR: Simulation crashed"
    log_file.write_text(error_msg)
    
    # Execution: Trigger telemetry collection with a simulated failure.
        with caplog.at_level(logging.INFO), \
            patch("sys.argv", ["script", "--state-file", str(state_file), "--exit-code", "1", "--log-file", str(log_file)]):
        with pytest.raises(SystemExit) as exc:
            record_telemetry.main()
        assert exc.value.code == 1
    
    # Verification: Validate that the telemetry record correctly ingested the error.
    runs_dir = base_dir / "failed_runs_archive"
    telemetry_file = list(runs_dir.glob("run_*/telemetry_results.json"))[0]
    
    with open(telemetry_file, "r") as f:
        data = json.load(f)
        assert data["status"] == "failed"
        assert data["error_log"] == error_msg

# ==============================================================================
# 4. Defensive Verification: Missing Log File
# ==============================================================================

# In this edge case, the simulator reports a failure, but the filesystem 
# lacks the expected log file. This constitutes an 'Environmental Mismatch'.
# The system must escalate this critical inconsistency before terminating.

def test_main_failure_missing_log_file(tmp_path, caplog):
    # Setup: Define the workspace structure without the expected log file.
    base_dir = tmp_path / "sim_run"
    config_dir = base_dir / "configs"
    config_dir.mkdir(parents=True)
    
    state_file = base_dir / "state.json"
    config_file = config_dir / "config_temp.json"
    config_file.write_text('{"params": "failure_mode"}')
    
    # We define a log file path that does not exist on disk.
    missing_log = base_dir / "missing_file.log"
    
    # Execute the telemetry routine.
        with caplog.at_level(logging.ERROR), \
            patch("sys.argv", ["script", "--state-file", str(state_file), "--exit-code", "1", "--log-file", str(missing_log)]):
        with pytest.raises(SystemExit) as exc:
            record_telemetry.main()
        
        # The system must escalate out with exit code 1 due to the missing evidence.
        assert exc.value.code == 1
    
    # Verify the specific error log was written, indicating an environmental mismatch.
    assert "❌ Environmental Mismatch: Simulation failed but log file not found" in caplog.text