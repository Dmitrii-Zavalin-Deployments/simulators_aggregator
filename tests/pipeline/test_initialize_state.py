import json
import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.pipeline import initialize_state

# ==============================================================================
# Narrative: Initialization State Machine Tests
# ==============================================================================

@pytest.fixture
def mock_filesystem(tmp_path, monkeypatch):
    # We establish a temporary working directory to mimic the repository root.
    # We monkeypatch the current working directory to ensure Path("tasks") 
    # resolves within this isolated environment.
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tasks").mkdir()
    (tmp_path / "repo").mkdir()
    return tmp_path

@pytest.fixture
def mock_tuner_state():
    # We mock the TunerState class to decouple testing from external state implementation:
    with patch("src.pipeline.initialize_state.TunerState") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        yield mock_instance

def test_discover_task_file_missing(mock_filesystem):
    # We define a scenario where the 'tasks/' directory contains no JSON files.
    # We expect the discover_task_file function to raise a FileNotFoundError.
    with pytest.raises(FileNotFoundError):
        initialize_state.discover_task_file()

def test_discover_task_file_success(mock_filesystem):
    # We create a valid task file within the 'tasks/' directory:
    task_path = mock_filesystem / "tasks" / "task.json"
    task_content = {"pipeline_id": "test_id", "input_data_list": ["data1.cad"]}
    task_path.write_text(json.dumps(task_content))
    
    # We verify that the function successfully reads and returns the task payload:
    result = initialize_state.discover_task_file()
    assert result["pipeline_id"] == "test_id"

def test_load_pipeline_manifest_failure(mock_filesystem):
    # We test the manifest discovery logic. We define a path that does not contain the manifest:
    repo_path = mock_filesystem / "repo"
    
    # We expect a FileNotFoundError when the manifest cannot be located via rglob:
    with pytest.raises(FileNotFoundError):
        initialize_state.load_pipeline_manifest(repo_path, "non_existent_id")

def test_execute_setup_script_success(mock_filesystem):
    # We test the provisioning script execution logic.
    # We mock subprocess.Popen to prevent actual shell execution during testing:
    repo_path = mock_filesystem / "repo"
    with patch("subprocess.Popen") as mock_popen:
        # We simulate a successful process execution (return code 0):
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # We execute the provisioner:
        initialize_state.execute_setup_script(repo_path, "setup.sh")
        
        # We verify that Popen was called with the correct command and working directory:
        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        assert "bash" in args[0]
        assert str(repo_path) == kwargs["cwd"]

def test_main_end_to_end_success(mock_filesystem, mock_tuner_state, monkeypatch):
    # We simulate a full integration run.
    # 1. We create the task file:
    (mock_filesystem / "tasks").mkdir(exist_ok=True)
    task_file = mock_filesystem / "tasks" / "task.json"
    task_file.write_text(json.dumps({"pipeline_id": "test_pid", "input_data_list": ["a.step"]}))
    
    # 2. We create a mock manifest file inside the repo:
    repo_path = mock_filesystem / "repo"
    repo_path.mkdir(exist_ok=True)
    manifest = repo_path / "test_pid.json"
    manifest.write_text(json.dumps([{"order": 1, "config": "cfg.json"}]))
    
    # 3. We create a mock config file:
    config_file = repo_path / "cfg.json"
    config_file.write_text("{}")
    
    # 4. We patch environment variables and CLI arguments to isolate execution:
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    with patch("sys.argv", ["script", "--repository-path", str(repo_path)]):
        with patch("subprocess.Popen"):
            # We execute the main orchestrator:
            initialize_state.main()
    
    # 5. We verify that the TunerState was instantiated with the expected task data:
    mock_tuner_state.save_to_disk.assert_called_once()