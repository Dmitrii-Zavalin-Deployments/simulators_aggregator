import json
import runpy
import pytest
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.pipeline import initialize_state
from src.pipeline.initialize_state import main

# ==============================================================================
# Infrastructure & Fixtures
# ==============================================================================

@pytest.fixture
def mock_filesystem(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tasks").mkdir(exist_ok=True)
    (tmp_path / "repo").mkdir(exist_ok=True)
    return tmp_path

@pytest.fixture
def mock_tuner_state():
    with patch("src.pipeline.initialize_state.TunerState") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        yield mock_instance

# ==============================================================================
# Task Discovery & Schema Validation
# ==============================================================================

def test_discover_task_file_corrupt_and_invalid_schema(mock_filesystem):
    tasks_dir = mock_filesystem / "tasks"
    
    (tasks_dir / "broken.json").write_text("{invalid_json_payload:")
    (tasks_dir / "unmapped.json").write_text(json.dumps({"unsupported_key": True}))
    
    with pytest.raises(ValueError, match="No JSON matching Tuner Task Schema found"):
        initialize_state.discover_task_file()

# ==============================================================================
# Subprocess Orchestration
# ==============================================================================

def test_execute_setup_script_stdout_streaming_and_failure(mock_filesystem):
    repo_path = mock_filesystem / "repo"
    
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_process.stdout = ["Provisioning dependency item A", "Compiling assets..."]
        mock_process.wait.return_value = 1
        mock_popen.return_value = mock_process
        
        with pytest.raises(subprocess.CalledProcessError):
            initialize_state.execute_setup_script(repo_path, "setup.sh")

# ==============================================================================
# Main Orchestrator Integrity
# ==============================================================================

def test_main_repo_path_not_exists(monkeypatch):
    monkeypatch.setenv("GITHUB_REF_NAME", "production")
    with patch("sys.argv", ["script", "--repo-path", "/missing/target/dir"]):
        with pytest.raises(SystemExit) as exc:
            initialize_state.main()
        assert exc.value.code == 1

def test_main_task_discovery_failure(mock_filesystem, monkeypatch):
    repo_path = mock_filesystem / "repo"
    monkeypatch.setenv("GITHUB_REF_NAME", "staging")
    with patch("sys.argv", ["script", "--repo-path", str(repo_path)]):
        with pytest.raises(SystemExit) as exc:
            initialize_state.main()
        assert exc.value.code == 1

# ==============================================================================
# Conditional Logic & Caching
# ==============================================================================

def test_main_cached_dependency_skips_provisioning(mock_filesystem, mock_tuner_state, monkeypatch):
    task_file = mock_filesystem / "tasks" / "task.json"
    task_file.write_text(json.dumps({"pipeline_id": "cached_pid", "input_data_list": []}))
    
    repo_path = mock_filesystem / "repo"
    manifest = repo_path / "cached_pid.json"
    manifest.write_text(json.dumps([{"order": 0, "setup_script": "install.sh", "config": "cfg.json"}]))
    (repo_path / "cfg.json").write_text("{}")
    
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    with patch("sys.argv", ["script", "--repo-path", str(repo_path), "--cached-dependency"]):
        with patch("src.pipeline.initialize_state.execute_setup_script") as mock_setup_exec:
            initialize_state.main()
            mock_setup_exec.assert_not_called()

# ==============================================================================
# Manifest & Configuration Lookups
# ==============================================================================

def test_main_config_basename_fallback(mock_filesystem, mock_tuner_state, monkeypatch):
    task_file = mock_filesystem / "tasks" / "task.json"
    task_file.write_text(json.dumps({"pipeline_id": "pid", "input_data_list": []}))
    
    repo_path = mock_filesystem / "repo"
    manifest = repo_path / "pid.json"
    manifest.write_text(json.dumps([{"order": 0, "config": "expected/nested/path/config.json"}]))
    
    drifted_dir = repo_path / "drifted_topology_folder"
    drifted_dir.mkdir()
    (drifted_dir / "config.json").write_text("{}")
    
    monkeypatch.setenv("GITHUB_REF_NAME", "dev")
    with patch("sys.argv", ["script", "--repo-path", str(repo_path)]):
        initialize_state.main()

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
    manifest.write_text(json.dumps([{"order": 0}]))
    
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    with patch("sys.argv", ["script", "--repo-path", str(repo_path)]):
        with pytest.raises(SystemExit) as exc:
            initialize_state.main()
        assert exc.value.code == 1

# ==============================================================================
# Exception Propagation
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
            mock_state_cls.side_effect = RuntimeError("Fatal state serialization mock failure")
            with pytest.raises(SystemExit) as exc:
                initialize_state.main()
            assert exc.value.code == 1

# ==============================================================================
# Entrypoint Execution
# ==============================================================================

def test_main_entrypoint_execution(mock_filesystem, mock_tuner_state, monkeypatch):
    task_file = mock_filesystem / "tasks" / "task.json"
    task_file.write_text(json.dumps({"pipeline_id": "pid", "input_data_list": []}))
    
    repo_path = mock_filesystem / "repo"
    manifest = repo_path / "pid.json"
    manifest.write_text(json.dumps([{"order": 0, "config": "cfg.json"}]))
    (repo_path / "cfg.json").write_text("{}")
    
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    script_file_path = Path(initialize_state.__file__)
    
    with patch("sys.argv", ["initialize_state.py", "--repo-path", str(repo_path)]):
        run_globals = runpy.run_path(str(script_file_path), run_name="__main__")
        assert run_globals is not None

# ==============================================================================
# Utility & Coverage Completion
# ==============================================================================

def test_fetch_inputs_from_dropbox_preserves_existing_files(mock_filesystem):
    input_list = ["test_a.cad", "test_b.step"]
    target_dir = mock_filesystem / "downloads"
    target_dir.mkdir(parents=True, exist_ok=True)

    for filename in input_list:
        (target_dir / filename).write_text("Authentic CAD Data")

    initialize_state.fetch_inputs_from_dropbox(input_list, target_dir)

    for filename in input_list:
        assert (target_dir / filename).exists(), f"{filename} was lost during verification"
        assert (target_dir / filename).read_text() == "Authentic CAD Data"

def test_fetch_inputs_from_dropbox_raises_error_if_missing(mock_filesystem):
    input_list = ["non_existent_file.cad"]
    target_dir = mock_filesystem / "empty_dir"
    target_dir.mkdir(parents=True, exist_ok=True)

    with pytest.raises(FileNotFoundError, match="missing from the target environment"):
        initialize_state.fetch_inputs_from_dropbox(input_list, target_dir)

def test_load_pipeline_manifest_raises_error_when_missing(mock_filesystem):
    repo_path = mock_filesystem / "repo"
    with pytest.raises(FileNotFoundError, match="not found"):
        initialize_state.load_pipeline_manifest(repo_path, "missing_pid")

def test_execute_setup_script_success_path(mock_filesystem):
    repo_path = mock_filesystem / "repo"
    script = repo_path / "test_success.sh"
    script.write_text("#!/bin/bash\necho 'done'")
    
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_process.stdout = ["line1"]
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        initialize_state.execute_setup_script(repo_path, "test_success.sh")

def test_main_executes_provisioning_when_not_cached(mock_filesystem, monkeypatch, mock_tuner_state):
    repo_path = mock_filesystem / "repo"
    repo_path.mkdir(exist_ok=True)
    
    (mock_filesystem / "tasks").mkdir(exist_ok=True)
    (mock_filesystem / "tasks" / "t.json").write_text(json.dumps({"pipeline_id": "p1", "input_data_list": []}))
    (repo_path / "p1.json").write_text(json.dumps([{"order": 1, "setup_script": "run.sh", "config": "c.json"}]))
    (repo_path / "c.json").write_text("{}")
    
    monkeypatch.setenv("GITHUB_REF_NAME", "test")
    
    with patch("sys.argv", ["main.py", "--repo-path", str(repo_path)]):
        with patch("src.pipeline.initialize_state.execute_setup_script") as mock_exec:
            initialize_state.main()
            mock_exec.assert_called_once()

# ==============================================================================
# Input Missing Diagnostic Test
# ==============================================================================

@patch("src.pipeline.initialize_state.load_pipeline_manifest")
@patch("src.pipeline.initialize_state.sys.exit")
@patch("src.pipeline.initialize_state.fetch_inputs_from_dropbox")
@patch("src.pipeline.initialize_state.discover_task_file")
@patch("src.pipeline.initialize_state.parse_arguments")
@patch("src.pipeline.initialize_state.Path.exists")
def test_main_exits_when_inputs_missing(
    mock_exists,
    mock_args,
    mock_discover,
    mock_fetch,
    mock_exit,
    mock_manifest
):
    """Verifies that a FileNotFoundError in input fetching halts execution immediately."""
    # 1. Setup deterministic mock behaviors
    mock_exists.return_value = True
    mock_args.return_value = MagicMock(repo_path="dummy/repo", cached_dependency=False)
    mock_discover.return_value = {
        "pipeline_id": "test_id", 
        "input_data_list": ["missing.cad"]
    }
    
    # 2. Force the targeted structural exception
    mock_fetch.side_effect = FileNotFoundError("CRITICAL: Input missing")

    # 3. Force mock_exit to raise SystemExit to mimic real process termination
    mock_exit.side_effect = SystemExit

    # 4. Execute entrypoint within exception wrapper
    with pytest.raises(SystemExit):
        main()

    # 5. Assert defensive boundary conditions
    mock_exit.assert_called_once_with(1)
    mock_manifest.assert_not_called()