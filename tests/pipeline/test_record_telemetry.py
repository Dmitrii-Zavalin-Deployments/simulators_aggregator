import json
import pytest
import logging
from unittest.mock import patch
from src.pipeline import record_telemetry

# ==============================================================================
# 1. Dormant State Verification
# ==============================================================================

# When the pipeline is triggered but no configuration file exists, the system 
# is effectively in a 'dormant' state. 
# It must exit gracefully with code 0, indicating that no telemetry processing 
# is required, without raising an exception.
def test_main_dormant_state(tmp_path, caplog):
    # We simulate a state file path, but intentionally do not generate 
    # the 'configs/config_temp.json' file.
    state_file = tmp_path / "state.json"
    log_file = tmp_path / "dummy.log"
    
    # We assert that the application terminates with exit code 0.
    with caplog.at_level(logging.INFO):
        with patch("sys.argv", ["script", "--state-file", str(state_file), "--exit-code", "0", "--log-file", str(log_file)]):
            with pytest.raises(SystemExit) as exc:
                record_telemetry.main()
            assert exc.value.code == 1
    
    # Verify the specific notice was logged to the console.
    assert "Notice: Temporary execution configuration file not found" in caplog.text

# ==============================================================================
# 2. Success Path Verification
# ==============================================================================

# In the 'happy path', the simulator has finished successfully (exit code 0).
# The system must perform the following:
#     1. Read the temporary configuration.
#     2. Generate a telemetry record in JSON format.
#     3. Perform housekeeping by removing the temporary configuration file.
def test_main_success_path(tmp_path, caplog):
    # Setup: Create the standard directory structure required by the pipeline.
    #     base_dir/configs/config_temp.json
    base_dir = tmp_path / "sim_run"
    config_dir = base_dir / "configs"
    config_dir.mkdir(parents=True)
    
    state_file = base_dir / "state.json"
    config_file = config_dir / "config_temp.json"
    log_file = base_dir / "execution.log"
    config_file.write_text('{"params": "test"}')
    
    # Execute the main orchestrator.
    with caplog.at_level(logging.INFO):
        with patch("sys.argv", ["script", "--state-file", str(state_file), "--exit-code", "0", "--log-file", str(log_file)]):
            with pytest.raises(SystemExit) as exc:
                record_telemetry.main()
            assert exc.value.code == 0
            
    # Verification:
    # 1. A new run record must exist inside a subfolder in the 'successful_runs_archive' directory.
    runs_dir = base_dir / "successful_runs_archive"
    assert runs_dir.exists()
    assert len(list(runs_dir.glob("run_*/telemetry_results.json"))) == 1
    
    # 2. The temporary configuration file must be purged.
    assert not config_file.exists()

# ==============================================================================
# 3. Failure Path Verification
# ==============================================================================

# When a simulator fails (exit code 1), we must extract the failure details.
# The system must capture the contents of the provided log file and embed them 
# into the generated telemetry JSON record for analysis.
def test_main_failure_path(tmp_path, caplog):
    # Setup: Create a filesystem environment containing an error log.
    base_dir = tmp_path / "sim_run"
    config_dir = base_dir / "configs"
    config_dir.mkdir(parents=True)
    
    state_file = base_dir / "state.json"
    config_file = config_dir / "config_temp.json"
    log_file = base_dir / "error.log"
    
    config_file.write_text('{"params": "failure_mode"}')
    error_msg = "CRITICAL ERROR: Simulation crashed"
    log_file.write_text(error_msg)
    
    # Execution:
    with caplog.at_level(logging.INFO):
        with patch("sys.argv", ["script", "--state-file", str(state_file), "--exit-code", "1", "--log-file", str(log_file)]):
            with pytest.raises(SystemExit) as exc:
                record_telemetry.main()
            # Assert failure code 1
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

# In this edge case, the simulator reports a failure, but the expected log file 
# is missing from the filesystem.
# The system must trigger an error log entry, indicating a critical mismatch 
# in the environment state, before exiting with code 1.
def test_main_failure_missing_log_file(tmp_path, caplog):
    """
    Targets line 69-70 branch coverage.
    Simulates a failed simulation run where the expected log file is missing.
    """
    # 1. Setup minimal directory workspace structure
    base_dir = tmp_path / "sim_run"
    config_dir = base_dir / "configs"
    config_dir.mkdir(parents=True)
    
    # 2. Setup state file and config staging assets
    state_file = base_dir / "state.json"
    config_file = config_dir / "config_temp.json"
    config_file.write_text('{"params": "failure_mode"}')
    
    # Define a log file path but do NOT write it to disk
    missing_log = base_dir / "missing_file.log"
    
    # 3. Execute with simulated sys.argv CLI inputs
    with caplog.at_level(logging.ERROR):
        with patch("sys.argv", ["script", "--state-file", str(state_file), "--exit-code", "1", "--log-file", str(missing_log)]):
            with pytest.raises(SystemExit) as exc:
                record_telemetry.main()
            
            # Confirms the script escalates out with exit code 1
            assert exc.value.code == 1
    
    # 4. Verify the line 70 error handling message was written to the stream
    assert "❌ Environmental Mismatch: Simulation failed but log file not found" in caplog.text