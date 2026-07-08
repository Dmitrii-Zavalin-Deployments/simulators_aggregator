import json
import runpy
import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.pipeline import initialize_state
from src.pipeline.initialize_state import main

# ==============================================================================
# Infrastructure & Fixtures
# ==============================================================================

# We establish an isolated sandbox root directory for clean filesystem operations
# to ensure that tests do not interfere with the host system.
@pytest.fixture
def mock_filesystem(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tasks").mkdir(exist_ok=True)
    (tmp_path / "repo").mkdir(exist_ok=True)
    return tmp_path

# To test the orchestration logic, we must decouple the initialization of the 
# TunerState container, replacing complex external state mutations with a 
# controllable MagicMock.
@pytest.fixture
def mock_tuner_state():
    with patch("src.pipeline.initialize_state.TunerState") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        yield mock_instance

# ==============================================================================
# Task Discovery & Schema Validation
# ==============================================================================

def test_discover_task_file_raises_error_when_empty(mock_filesystem):
    """Verifies that a FileNotFoundError is raised if no task files exist."""
    with pytest.raises(FileNotFoundError, match="No JSON files found in tasks/"):
        initialize_state.discover_task_file()


def test_discover_task_file_raises_error_when_multiple_files(mock_filesystem):
    """Verifies that a ValueError is raised if more than 1 task file is present."""
    tasks_dir = mock_filesystem / "tasks"
    (tasks_dir / "task1.json").write_text(json.dumps({"pipeline_id": "p1", "input_data_list": []}))
    (tasks_dir / "task2.json").write_text(json.dumps({"pipeline_id": "p2", "input_data_list": []}))
    
    with pytest.raises(ValueError, match="Multiple task files found in tasks/ directory"):
        initialize_state.discover_task_file()


def test_discover_task_file_corrupt_json(mock_filesystem):
    """Verifies that invalid/corrupt JSON throws a descriptive ValueError."""
    tasks_dir = mock_filesystem / "tasks"
    (tasks_dir / "broken.json").write_text("{invalid_json_payload:")
    
    with pytest.raises(ValueError, match="contains invalid JSON"):
        initialize_state.discover_task_file()


def test_discover_task_file_raises_error_if_root_is_list(mock_filesystem):
    """Verifies strict schema contract rejection if root element is a JSON list."""
    tasks_dir = mock_filesystem / "tasks"
    (tasks_dir / "list_root.json").write_text(json.dumps([{"pipeline_id": "p1", "input_data_list": []}]))
    
    with pytest.raises(ValueError, match="root element must be a JSON object, not a list"):
        initialize_state.discover_task_file()


def test_discover_task_file_invalid_schema_keys(mock_filesystem):
    """Verifies that a task file missing required schema tracking keys is rejected."""
    tasks_dir = mock_filesystem / "tasks"
    (tasks_dir / "unmapped.json").write_text(json.dumps({"unsupported_key": True}))
    
    with pytest.raises(ValueError, match="is missing required schema keys"):
        initialize_state.discover_task_file()

# ==============================================================================
# Downstream Manifest Parsers Validation
# ==============================================================================

def test_load_pipeline_manifest_raises_error_when_missing(mock_filesystem):
    """Verifies descriptive FileNotFoundError logging when a pipeline target is missing."""
    repo_path = mock_filesystem / "repo"
    with pytest.raises(FileNotFoundError, match="not found"):
        initialize_state.load_pipeline_manifest(repo_path, "missing_pid")


def test_load_pipeline_manifest_corrupt_json(mock_filesystem):
    """Verifies that invalid manifest files crash downstream configurations cleanly."""
    repo_path = mock_filesystem / "repo"
    (repo_path / "corrupt_manifest.json").write_text("{broken_object:")
    
    with pytest.raises(ValueError, match="contains invalid JSON"):
        initialize_state.load_pipeline_manifest(repo_path, "corrupt_manifest")


def test_load_pipeline_manifest_requires_object_root(mock_filesystem):
    """Verifies strict adherence to Object contracts inside manifest documents."""
    repo_path = mock_filesystem / "repo"
    (repo_path / "legacy_array.json").write_text(json.dumps([{"config": "c.json"}]))
    
    with pytest.raises(ValueError, match="root element must be a JSON object"):
        initialize_state.load_pipeline_manifest(repo_path, "legacy_array")

# ==============================================================================
# Subprocess Orchestration
# ==============================================================================

# During the provisioning phase, the system uses subprocess to execute bash scripts.
# We must ensure that output is correctly streamed for logs and that non-zero
# exit codes correctly trigger a CalledProcessError, preventing the pipeline 
# from continuing in a broken state.
def test_execute_setup_script_stdout_streaming_and_failure(mock_filesystem):
    """Verifies output streaming and generation of a CalledProcessError upon failure."""
    repo_path = mock_filesystem / "repo"
    
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_process.stdout = ["Provisioning dependency item A", "Compiling assets..."]
        mock_process.wait.return_value = 1
        mock_popen.return_value = mock_process
        
        with pytest.raises(subprocess.CalledProcessError):
            initialize_state.execute_setup_script(repo_path, "setup.sh")


def test_execute_setup_script_success_path(mock_filesystem):
    """Confirms that successful return codes evaluate without throwing validation issues."""
    repo_path = mock_filesystem / "repo"
    script = repo_path / "test_success.sh"
    script.write_text("#!/bin/bash\necho 'done'")
    
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_process.stdout = ["line1"]
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        initialize_state.execute_setup_script(repo_path, "test_success.sh")

# ==============================================================================
# Main Orchestrator Integrity
# ==============================================================================

# The entry point must enforce strict environment validation. 
# If the provided repository path does not exist, or if the system cannot locate 
# any valid tasks to initialize, the main process must terminate with a system exit code of 1.
def test_main_repo_path_not_exists(monkeypatch):
    """Verifies that missing repository targets exit cleanly with status 1."""
    monkeypatch.setenv("GITHUB_REF_NAME", "production")
    with patch("sys.argv", ["script", "--repo-path", "/missing/target/dir"]):
        with pytest.raises(SystemExit) as exc:
            initialize_state.main()
        assert exc.value.code == 1


def test_main_task_discovery_failure(mock_filesystem, monkeypatch):
    """Verifies main pipeline short-circuits gracefully if task discovery fails."""
    repo_path = mock_filesystem / "repo"
    monkeypatch.setenv("GITHUB_REF_NAME", "staging")
    with patch("sys.argv", ["script", "--repo-path", str(repo_path)]):
        with pytest.raises(SystemExit) as exc:
            initialize_state.main()
        assert exc.value.code == 1

# ==============================================================================
# Conditional Logic & Caching
# ==============================================================================

# When the dependency cache is flagged as active (cached_dependency=True), 
# the pipeline optimization should bypass provisioning scripts. We assert that
# the setup function is never called when the cache is hit.
def test_main_cached_dependency_skips_provisioning(mock_filesystem, mock_tuner_state, monkeypatch):
    """Verifies provisioning scripts are bypassed when cached_dependency is flagged true."""
    task_file = mock_filesystem / "tasks" / "task.json"
    task_file.write_text(json.dumps({"pipeline_id": "cached_pid", "input_data_list": []}))
    
    repo_path = mock_filesystem / "repo"
    manifest = repo_path / "cached_pid.json"
    manifest.write_text(json.dumps({"setup_script": "install.sh", "config": "cfg.json", "execution_chain": []}))
    (repo_path / "cfg.json").write_text("{}")
    
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    with patch("sys.argv", ["script", "--repo-path", str(repo_path), "--cached-dependency"]):
        with patch("src.pipeline.initialize_state.execute_setup_script") as mock_setup_exec:
            initialize_state.main()
            mock_setup_exec.assert_not_called()


def test_main_executes_provisioning_when_not_cached(mock_filesystem, monkeypatch, mock_tuner_state):
    """Verifies that hydration scripts execute properly when cache context is empty."""
    repo_path = mock_filesystem / "repo"
    repo_path.mkdir(exist_ok=True)
    
    (mock_filesystem / "tasks").mkdir(exist_ok=True)
    (mock_filesystem / "tasks" / "t.json").write_text(json.dumps({"pipeline_id": "p1", "input_data_list": []}))
    (repo_path / "p1.json").write_text(json.dumps({"setup_script": "run.sh", "config": "c.json", "execution_chain": [{"order": 1, "repository_url": "mock"}]}))
    (repo_path / "c.json").write_text("{}")
    
    monkeypatch.setenv("GITHUB_REF_NAME", "test")
    
    with patch("sys.argv", ["main.py", "--repo-path", str(repo_path)]):
        with patch("src.pipeline.initialize_state.execute_setup_script") as mock_exec:
            initialize_state.main()
            mock_exec.assert_called_once_with(repo_path, "run.sh")

# ==============================================================================
# Manifest & Configuration Lookups
# ==============================================================================

# If a configuration file is missing from its expected path, the system performs 
# an automatic fallback search using the filename. We simulate a drifted topology
# to verify this fallback succeeds.
def test_main_config_basename_fallback(mock_filesystem, mock_tuner_state, monkeypatch):
    """Verifies that drifted path layouts fallback gracefully onto filename rglob searches."""
    task_file = mock_filesystem / "tasks" / "task.json"
    task_file.write_text(json.dumps({"pipeline_id": "pid", "input_data_list": []}))
    
    repo_path = mock_filesystem / "repo"
    manifest = repo_path / "pid.json"
    manifest.write_text(json.dumps({"config": "expected/nested/path/config.json", "execution_chain": []}))
    
    drifted_dir = repo_path / "drifted_topology_folder"
    drifted_dir.mkdir()
    (drifted_dir / "config.json").write_text("{}")
    
    monkeypatch.setenv("GITHUB_REF_NAME", "dev")
    with patch("sys.argv", ["script", "--repo-path", str(repo_path)]):
        initialize_state.main()

# When the manifest points to a configuration file that cannot be found 
# even after fallback, or if the manifest lacks the baseline configuration key,
# the system must protect the integrity of the run by forcing a SystemExit.
def test_main_config_file_missing_exit(mock_filesystem, monkeypatch):
    """Enforces direct termination if a configuration target cannot be localized."""
    task_file = mock_filesystem / "tasks" / "task.json"
    task_file.write_text(json.dumps({"pipeline_id": "pid", "input_data_list": []}))
    
    repo_path = mock_filesystem / "repo"
    manifest = repo_path / "pid.json"
    manifest.write_text(json.dumps({"config": "does_not_exist.json"}))
    
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    with patch("sys.argv", ["script", "--repo-path", str(repo_path)]):
        with pytest.raises(SystemExit) as exc:
            initialize_state.main()
        assert exc.value.code == 1


def test_main_manifest_missing_config_exit(mock_filesystem, monkeypatch):
    """Enforces exit policies if manifest schemas omit mandatory configuration references."""
    task_file = mock_filesystem / "tasks" / "task.json"
    task_file.write_text(json.dumps({"pipeline_id": "pid", "input_data_list": []}))
    
    repo_path = mock_filesystem / "repo"
    manifest = repo_path / "pid.json"
    manifest.write_text(json.dumps({"execution_chain": []}))
    
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    with patch("sys.argv", ["script", "--repo-path", str(repo_path)]):
        with pytest.raises(SystemExit) as exc:
            initialize_state.main()
        assert exc.value.code == 1

# ==============================================================================
# Exception Propagation
# ==============================================================================

# Any failure during the instantiation of the Sovereign State container should 
# be caught. We simulate a RuntimeError to ensure the orchestrator exits cleanly 
# rather than propagating the crash to the parent shell.
def test_main_tuner_state_exception_exit(mock_filesystem, monkeypatch):
    """Ensures internal serialization errors wrap cleanly into explicit process codes."""
    task_file = mock_filesystem / "tasks" / "task.json"
    task_file.write_text(json.dumps({"pipeline_id": "pid", "input_data_list": []}))
    
    repo_path = mock_filesystem / "repo"
    manifest = repo_path / "pid.json"
    manifest.write_text(json.dumps({"config": "cfg.json", "execution_chain": []}))
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

# Finally, we confirm the module can be executed directly. By using runpy, 
# we simulate a shell call to 'python initialize_state.py', ensuring the
# __name__ == "__main__" block triggers the main logic.
def test_main_entrypoint_execution(mock_filesystem, mock_tuner_state, monkeypatch):
    """Validates entry point activation when executing via shell modules directly."""
    task_file = mock_filesystem / "tasks" / "task.json"
    task_file.write_text(json.dumps({"pipeline_id": "pid", "input_data_list": []}))
    
    repo_path = mock_filesystem / "repo"
    manifest = repo_path / "pid.json"
    manifest.write_text(json.dumps({"config": "cfg.json", "execution_chain": []}))
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
    """Verifies that the function respects/preserves authentic assets that already exist."""
    input_list = ["test_a.cad", "test_b.step"]
    target_dir = mock_filesystem / "downloads"
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Pre-seed the environment with authentic data
    for filename in input_list:
        (target_dir / filename).write_text("Authentic CAD Data")

    # 2. Act
    initialize_state.fetch_inputs_from_dropbox(input_list, target_dir)

    # 3. Assert they were not touched/overwritten/deleted
    for filename in input_list:
        assert (target_dir / filename).exists(), f"{filename} was lost during verification"
        assert (target_dir / filename).read_text() == "Authentic CAD Data"


def test_fetch_inputs_from_dropbox_raises_credential_error_if_env_missing(mock_filesystem, monkeypatch):
    """Verifies that an OSError/EnvironmentError is triggered if required credentials are absent."""
    # Ensure environment keys are strictly cleared for this test case
    monkeypatch.delenv("DROPBOX_APP_KEY", raising=False)
    monkeypatch.delenv("DROPBOX_APP_SECRET", raising=False)
    monkeypatch.delenv("DROPBOX_REFRESH_TOKEN", raising=False)
    
    input_list = ["missing_asset.step"]
    target_dir = mock_filesystem / "empty_dir"
    target_dir.mkdir(parents=True, exist_ok=True)

    with pytest.raises(OSError, match="Missing required Dropbox credentials"):
        initialize_state.fetch_inputs_from_dropbox(input_list, target_dir)


def test_fetch_inputs_from_dropbox_raises_error_if_missing(mock_filesystem, monkeypatch):
    """Verifies that the system raises a hard FileNotFoundError if the asset is missing from Dropbox."""
    # 1. Seed dummy credentials via monkeypatch to bypass the initial environment block
    monkeypatch.setenv("DROPBOX_APP_KEY", "mock_key")
    monkeypatch.setenv("DROPBOX_APP_SECRET", "mock_secret")
    monkeypatch.setenv("DROPBOX_REFRESH_TOKEN", "mock_refresh")
    monkeypatch.setenv("DROPBOX_FOLDER", "simulators")
    
    input_list = ["non_existent_file.cad"]
    target_dir = mock_filesystem / "empty_dir"
    target_dir.mkdir(parents=True, exist_ok=True)

    # 2. Intercept and mock the network infrastructure components deterministically
    with patch("src.io.dropbox_utils.TokenManager"), \
         patch("src.io.download_from_dropbox.CloudIngestor") as mock_ingestor_cls:
        
        # Configure the mock ingestor to throw a remote API error
        mock_ingestor = MagicMock()
        mock_ingestor.download_file.side_effect = Exception("Remote file target not found on Dropbox")
        mock_ingestor_cls.return_value = mock_ingestor

        # 3. Assert that the function wraps the network failure into the expected FileNotFoundError
        with pytest.raises(FileNotFoundError, match="Failed to download asset"):
            initialize_state.fetch_inputs_from_dropbox(input_list, target_dir)


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
    mock_exists,        # Maps to Path.exists
    mock_args,          # Maps to parse_arguments
    mock_discover,      # Maps to discover_task_file
    mock_fetch,         # Maps to fetch_inputs_from_dropbox
    mock_exit,          # Maps to sys.exit
    mock_manifest,      # Maps to load_pipeline_manifest
    mock_filesystem     # <--- ADD THIS FIXTURE
):
    """Verifies that a FileNotFoundError in input fetching triggers an explicit exit(1)."""
    # 1. Configure deterministic mock behaviors
    mock_exists.return_value = True
    
    # FIX: Use the actual temporary directory from the fixture instead of a hardcoded string
    repo_dir = mock_filesystem / "repo"
    repo_dir.mkdir(exist_ok=True) # Ensure it exists physically for Path()
    
    mock_args.return_value = MagicMock(
        repo_path=str(repo_dir), 
        cached_dependency=False
    )
    
    mock_discover.return_value = {
        "pipeline_id": "test_id", 
        "input_data_list": ["missing.cad"]
    }

    mock_manifest.return_value = {
        "config": "cfg.json",
        "setup_script": None,
        "execution_chain": []
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
    mock_manifest.assert_called_once()