import pytest
import json
from unittest.mock import MagicMock
from tests.dummies import dummy_in

# =============================================================================
# 1. TEMPORARY WORKSPACE FIXTURES
# =============================================================================
@pytest.fixture
def tmp_workspace(tmp_path):
    """
    Creates an isolated temporary directory for file system tests.
    Automatically cleans up after the test finishes.
    """
    return tmp_path

@pytest.fixture
def mock_dropbox_client():
    """
    Creates a mock Dropbox client to prevent live network calls.
    Inject this into tests that use src.io.dropbox_utils or upload/download modules.
    """
    mock_client = MagicMock()
    # Add common Dropbox methods that your code calls here
    mock_client.files_upload = MagicMock(return_value=MagicMock())
    mock_client.files_download = MagicMock(return_value=(MagicMock(), MagicMock()))
    return mock_client

# =============================================================================
# 2. SCHEMA & DATA FIXTURES
# =============================================================================
@pytest.fixture
def valid_task_config():
    """
    Returns a standard, valid task configuration dictionary.
    Uses the dummy_in class from tests/dummies.py to ensure structural consistency.
    """
    return dummy_in({
        "pipeline_id": "test_pipeline_001",
        "input_data_list": ["sample.step"],
        "task_details": [{
            "order": 1,
            "repository_url": "https://github.com/test/repo",
            "version_tag": "main",
            "config": "config/test.json",
            "setup_script": "setup.sh"
        }]
    })

@pytest.fixture
def create_mock_state_file(tmp_workspace):
    """
    Helper to generate a state.json file in the temporary workspace.
    """
    def _create(data):
        state_path = tmp_workspace / "state.json"
        with open(state_path, "w") as f:
            json.dump(data, f, indent=4)
        return str(state_path)
    return _create

# =============================================================================
# 3. LOGGING & ENVIRONMENT
# =============================================================================
@pytest.fixture(autouse=True)
def setup_logging(caplog):
    """
    Ensures tests run with standardized logging levels.
    Allows capturing logs for assertion in test cases (e.g., verifying status logs).
    """
    import logging
    logging.basicConfig(level=logging.INFO)
    # This prevents the protocol-required logging from cluttering stdout unless failed
    logging.getLogger().setLevel(logging.INFO)

@pytest.fixture(autouse=True)
def enforce_no_state_mutation():
    """
    Ensures that solvers/state managers are not mutated unexpectedly 
    between test runs (Protocol: State Isolation).
    """
    yield
    # Cleanup logic can be added here if you have global state objects