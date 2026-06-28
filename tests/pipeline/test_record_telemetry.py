import json
import pytest
import logging
from unittest.mock import patch
from src.pipeline import record_telemetry

# ==============================================================================
# 1. Dormant State Verification
# ==============================================================================

# Scenario: The pipeline is triggered in a state where no configuration exists.
# The system must exit gracefully (0) and log the status without crashing.
def test_main_dormant_state(tmp_path, caplog):
    # Setup paths: state file is required, but we won't create config_temp.json
    state_file = tmp_path / "state.json"
    log_file = tmp_path / "dummy.log"
    
    with caplog.at_level(logging.INFO):
        with patch("sys.argv", ["script", "--state-file", str(state_file), "--exit-code", "0", "--log-file", str(log_file)]):
            # Expect sys.exit(0)
            with pytest.raises(SystemExit) as exc:
                record_telemetry.main()
            assert exc.value.code == 0
    
    assert "Notice: No temporary config file found" in caplog.text

# ==============================================================================
# 2. Success Path Verification
# ==============================================================================

# Scenario: The simulator finished successfully (exit code 0).
# The system must read the config, generate a telemetry record, and remove the temp file.
def test_main_success_path(tmp_path, caplog):
    # Create the required directory structure: base/config/config_temp.json
    base_dir = tmp_path / "sim_run"
    config_dir = base_dir / "config"
    config_dir.mkdir(parents=True)
    
    state_file = base_dir / "state.json"
    config_file = config_dir / "config_temp.json"
    log_file = base_dir / "execution.log"
    
    # Create a dummy config
    config_file.write_text('{"params": "test"}')
    
    with caplog.at_level(logging.INFO):
        with patch("sys.argv", ["script", "--state-file", str(state_file), "--exit-code", "0", "--log-file", str(log_file)]):
            with pytest.raises(SystemExit) as exc:
                record_telemetry.main()
            assert exc.value.code == 0
            
    # Verify the telemetry file was created in the successful_runs folder
    runs_dir = base_dir / "successful_runs"
    assert runs_dir.exists()
    assert len(list(runs_dir.glob("run_*_success.json"))) == 1
    
    # Verify cleanup: config_temp.json should be gone
    assert not config_file.exists()

# ==============================================================================
# 3. Failure Path Verification
# ==============================================================================

# Scenario: The simulator failed (exit code 1).
# The system must capture the log file content into the JSON and exit with status 1.
def test_main_failure_path(tmp_path, caplog):
    base_dir = tmp_path / "sim_run"
    config_dir = base_dir / "config"
    config_dir.mkdir(parents=True)
    
    state_file = base_dir / "state.json"
    config_file = config_dir / "config_temp.json"
    log_file = base_dir / "error.log"
    
    config_file.write_text('{"params": "failure_mode"}')
    log_file.write_text("CRITICAL ERROR: Simulation crashed")
    
    with caplog.at_level(logging.INFO):
        with patch("sys.argv", ["script", "--state-file", str(state_file), "--exit-code", "1", "--log-file", str(log_file)]):
            with pytest.raises(SystemExit) as exc:
                record_telemetry.main()
            assert exc.value.code == 1
    
    # Verify the telemetry record contains the error log
    runs_dir = base_dir / "successful_runs"
    telemetry_file = list(runs_dir.glob("run_*_failed.json"))[0]
    
    with open(telemetry_file, "r") as f:
        data = json.load(f)
        assert data["status"] == "failed"
        assert data["error_log"] == "CRITICAL ERROR: Simulation crashed"

# Scenario: The simulator reported a failure, but the expected log file is missing.
# This covers the critical error branch at line 52 where the system logs that 
# the log file could not be found.
def test_main_failure_missing_log_file(tmp_path, caplog):
    # Setup necessary file structure so we pass the "dormant" and "file exist" checks
    base_dir = tmp_path / "sim_run"
    config_dir = base_dir / "config"
    config_dir.mkdir(parents=True)
    
    state_file = base_dir / "state.json"
    config_file = config_dir / "config_temp.json"
    config_file.write_text('{"params": "failure_mode"}')
    
    # Path for a log file that definitely does not exist
    missing_log = base_dir / "missing_file.log"
    
    with caplog.at_level(logging.ERROR):
        # We pass exit-code 1 to trigger the "failed" status
        with patch("sys.argv", ["script", "--state-file", str(state_file), "--exit-code", "1", "--log-file", str(missing_log)]):
            with pytest.raises(SystemExit) as exc:
                record_telemetry.main()
            # Assert failure code 1
            assert exc.value.code == 1
    
    # Assert the specific error log line (Line 52) was triggered
    assert "❌ Simulation failed but log file not found" in caplog.text