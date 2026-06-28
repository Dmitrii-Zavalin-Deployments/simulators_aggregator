import os
import json
import sys
import runpy
import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.pipeline import initialize_state

# ==============================================================================
# Shared Fixtures & Configuration
# ==============================================================================

@pytest.fixture
def mock_filesystem(tmp_path, monkeypatch):
    """Establishes an isolated sandbox root directory for clean filesystem operations."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tasks").mkdir(exist_ok=True)
    (tmp_path / "repo").mkdir(exist_ok=True)
    return tmp_path

@pytest.fixture
def mock_tuner_state():
    """Decouples external module state mutations from core orchestration pipeline tests."""
    with patch("src.pipeline.initialize_state.TunerState") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        yield mock_instance

# ==============================================================================
# 1. Target: Lines 50-52 (JSON Decode Failures & Missing Schema Valuations)
# ==============================================================================

def test_discover_task_file_corrupt_and_invalid_schema(mock_filesystem):
    tasks_dir = mock_filesystem / "tasks"
    
    # Write a broken JSON file to force json.JSONDecodeError branch (Lines 50-51)
    (tasks_dir / "broken.json").write_text("{invalid_json_payload:")
    
    # Write an unmapped JSON schema file to trigger the trailing ValueError (Line 52)
    (tasks_dir / "unmapped.json").write_text(json.dumps({"unsupported_key": True}))
    
    with pytest.raises(ValueError, match="No JSON matching Tuner Task Schema found"):
        initialize_state.discover_task_file()

# ==============================================================================
# 2. Target: Lines 115 & 119 (Subprocess Log Streaming & CalledProcessError Exits)
# ==============================================================================

def test_execute_setup_script_stdout_streaming_and_failure(mock_filesystem):
    repo_path = mock_filesystem / "repo"
    
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        # Feed mock stdout lines to execute real-time loop streaming (Line 115)
        mock_process.stdout = ["Provisioning dependency item A", "Compiling assets..."]
        # Return bad termination code to trigger execution exceptions (Line 119)
        mock_process.wait.return_value = 1
        mock_popen.return_value = mock_process
        
        with pytest.raises(subprocess.CalledProcessError):
            initialize_state.execute_setup_script(repo_path, "setup.sh")

# ==============================================================================
# 3. Target: Lines 132-133 & 141-143 (Orchestration Initial Missing Path/Task Crashes)
# ==============================================================================

def test_main_repo_path_not_exists(monkeypatch):
    monkeypatch.setenv("GITHUB_REF_NAME", "production")
    # Simulate CLI argument passing an invalid path location (Lines 132-133)
    with patch("sys.argv", ["script", "--repo-path", "/missing/target/dir"]):
        with pytest.raises(SystemExit) as exc:
            initialize_state.main()
        assert exc.value.code == 1

def test_main_task_discovery_failure(mock_filesystem, monkeypatch):
    repo_path = mock_filesystem / "repo"
    monkeypatch.setenv("GITHUB_REF_NAME", "staging")
    # Leave tasks directory empty to trigger immediate hard orchestration exit (Lines 141-143)
    with patch("sys.argv", ["script", "--repo-path", str(repo_path)]):
        with pytest.raises(SystemExit) as exc:
            initialize_state.main()
        assert exc.value.code == 1

# ==============================================================================
# 4. Target: Lines 164-167 (Conda Cache Hit vs Conditional Provisioning Branch)
# ==============================================================================

def test_main_cached_dependency_skips_provisioning(mock_filesystem, mock_tuner_state, monkeypatch):
    task_file = mock_filesystem / "tasks" / "task.json"
    task_file.write_text(json.dumps({"pipeline_id": "cached_pid", "input_data_list": []}))
    
    repo_path = mock_filesystem / "repo"
    manifest = repo_path / "cached_pid.json"
    manifest.write_text(json.dumps([{"order": 0, "setup_script": "install.sh", "config": "cfg.json"}]))
    (repo_path / "cfg.json").write_text("{}")
    
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    # Pass execution arguments explicitly claiming environment dependency cache hits (Lines 165-167)
    with patch("sys.argv", ["script", "--repo-path", str(repo_path), "--cached-dependency"]):
        with patch("src.pipeline.initialize_state.execute_setup_script") as mock_setup_exec:
            initialize_state.main()
            mock_setup_exec.assert_not_called()

# ==============================================================================
# 5. Target: Line 182 (Config Lookup Basename Fallback Route Match)
# ==============================================================================

def test_main_config_basename_fallback(mock_filesystem, mock_tuner_state, monkeypatch):
    task_file = mock_filesystem / "tasks" / "task.json"
    task_file.write_text(json.dumps({"pipeline_id": "pid", "input_data_list": []}))
    
    repo_path = mock_filesystem / "repo"
    manifest = repo_path / "pid.json"
    manifest.write_text(json.dumps([{"order": 0, "config": "expected/nested/path/config.json"}]))
    
    # Intentionally misalign file topology to force absolute fallback matching (Line 181-182)
    drifted_dir = repo_path / "drifted_topology_folder"
    drifted_dir.mkdir()
    (drifted_dir / "config.json").write_text("{}")
    
    monkeypatch.setenv("GITHUB_REF_NAME", "dev")
    with patch("sys.argv", ["script", "--repo-path", str(repo_path)]):
        initialize_state.main()

# ==============================================================================
# 6. Target: Lines 188-192 (Schema Violations & Configuration Absence Enforcements)
# ==============================================================================

def test_main_config_file_missing_exit(mock_filesystem, monkeypatch):
    task_file = mock_filesystem / "tasks" / "task.json"
    task_file.write_text(json.dumps({"pipeline_id": "pid", "input_data_list": []}))
    
    repo_path = mock_filesystem / "repo"
    manifest = repo_path / "pid.json"
    manifest.write_text(json.dumps([{"order": 0, "config": "does_not_exist.json"}]))
    
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    with patch("sys.argv", ["script", "--repo-path", str(repo_path)]):
        with pytest.raises(SystemExit) as exc:
            initialize_state.main()
        assert exc.value.code == 1

def test_main_manifest_missing_config_exit(mock_filesystem, monkeypatch):
    task_file = mock_filesystem / "tasks" / "task.json"
    task_file.write_text(json.dumps({"pipeline_id": "pid", "input_data_list": []}))
    
    repo_path = mock_filesystem / "repo"
    manifest = repo_path / "pid.json"
    manifest.write_text(json.dumps([{"order": 0}]))  # Explicitly omitted layout baseline config key
    
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    with patch("sys.argv", ["script", "--repo-path", str(repo_path)]):
        with pytest.raises(SystemExit) as exc:
            initialize_state.main()
        assert exc.value.code == 1

# ==============================================================================
# 7. Target: Lines 209-211 (State Packaging Error Propagation Exits)
# ==============================================================================

def test_main_tuner_state_exception_exit(mock_filesystem, monkeypatch):
    task_file = mock_filesystem / "tasks" / "task.json"
    task_file.write_text(json.dumps({"pipeline_id": "pid", "input_data_list": []}))
    
    repo_path = mock_filesystem / "repo"
    manifest = repo_path / "pid.json"
    manifest.write_text(json.dumps([{"order": 0, "config": "cfg.json"}]))
    (repo_path / "cfg.json").write_text("{}")
    
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    with patch("sys.argv", ["script", "--repo-path", str(repo_path)]):
        with patch("src.pipeline.initialize_state.TunerState") as mock_state_cls:
            # Inject a fatal initialization failure inside the data schema builder
            mock_state_cls.side_effect = RuntimeError("Fatal state serialization mock failure")
            with pytest.raises(SystemExit) as exc:
                initialize_state.main()
            assert exc.value.code == 1

# ==============================================================================
# 8. Target: Line 215 (Direct Script Execution Entrypoint Validation)
# ==============================================================================

def test_main_entrypoint_execution(mock_filesystem, mock_tuner_state, monkeypatch):
    task_file = mock_filesystem / "tasks" / "task.json"
    task_file.write_text(json.dumps({"pipeline_id": "pid", "input_data_list": []}))
    
    repo_path = mock_filesystem / "repo"
    manifest = repo_path / "pid.json"
    manifest.write_text(json.dumps([{"order": 0, "config": "cfg.json"}]))
    (repo_path / "cfg.json").write_text("{}")
    
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    
    # Locate actual script path source file target location dynamically
    script_file_path = Path(initialize_state.__file__)
    
    with patch("sys.argv", ["initialize_state.py", "--repo-path", str(repo_path)]):
        # Execute runpy simulation to force execution of the entry point block (Line 214-215)
        run_globals = runpy.run_path(str(script_file_path), run_name="__main__")
        assert run_globals is not None