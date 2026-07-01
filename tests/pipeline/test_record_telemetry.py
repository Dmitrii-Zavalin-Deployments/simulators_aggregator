import json
import pytest
import logging
from unittest.mock import patch, MagicMock
from src.pipeline import record_telemetry
from src.pipeline.record_telemetry import main

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
            assert exc.value.code == 0
    
    # Verify the specific notice was logged to the console.
    assert "Notice: No temporary config file found" in caplog.text

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
    # Setup: Create config but provide a path to a non-existent log file.
    base_dir = tmp_path / "sim_run"
    config_dir = base_dir / "configs"
    config_dir.mkdir(parents=True)
    
    state_file = base_dir / "state.json"
    config_file = config_dir / "config_temp.json"
    config_file.write_text('{"params": "failure_mode"}')
    missing_log = base_dir / "missing_file.log"
    
    # Execution:
    with caplog.at_level(logging.ERROR):
        with patch("sys.argv", ["script", "--state-file", str(state_file), "--exit-code", "1", "--log-file", str(missing_log)]):
            with pytest.raises(SystemExit) as exc:
                record_telemetry.main()
            # Assert failure code 1
            assert exc.value.code == 1
    
    # Verification: Assert the specific logger.error() call (Line 52) was triggered.
    assert "❌ Environmental Mismatch: Simulation failed but log file not found" in caplog.text

@patch("src.pipeline.record_telemetry.os.path.exists")
@patch("src.pipeline.record_telemetry.argparse.ArgumentParser.parse_args")
@patch("src.pipeline.record_telemetry.open", create=True)
@patch("src.pipeline.record_telemetry.os.makedirs")
@patch("src.pipeline.record_telemetry.json.dump")
def test_main_failure_missing_log_file(mock_json_dump, mock_makedirs, mock_open, mock_args, mock_exists, caplog):
    """
    Triggers the missing line 69 by simulating a failed execution (exit_code=1)
    where the specific log file path does not exist on disk.
    """
    # 1. Setup Arguments
    mock_args.return_value = MagicMock(
        state_file="path/to/state.json",
        exit_code=1,
        log_file="non_existent.log"
    )

    # 2. Configure mock_exists logic:
    # - True for directory/config checks (to proceed past initial steps)
    # - False for the specific log file (to hit line 69)
    def side_effect_exists(path):
        if path == "non_existent.log":
            return False
        return True
    mock_exists.side_effect = side_effect_exists

    # 3. Execute main and handle the SystemExit(1) at the end
    with pytest.raises(SystemExit) as exc:
        main()
    
    assert exc.value.code == 1
    
    # 4. Assert the exact error log was triggered
    assert "❌ Environmental Mismatch: Simulation failed but log file not found" in caplog.text