# tests/behavior/test_domain_gates.py

import pytest
import json
from src.core.state_engine import OrchestrationState

def test_dummy_disc_agnostic_execution(tmp_path):
    """
    Verification: Agnostic Execution Mandate.
    Ensures the engine handles 'future_project_x' exactly like any other.
    """
    # Setup paths
    config_path = tmp_path / "active_disk.json"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    ledger_path = tmp_path / "orchestration_ledger.json"
    
    # Create config for a "Future Project"
    config_path.write_text(json.dumps({
        "project_id": "future_project_x",
        "manifest_url": "http://mock-remote-manifest.com"
    }))

    # Mount the engine (Agnostic Initialization)
    state = OrchestrationState(str(config_path), str(data_dir), str(ledger_path))
    
    # Mock Hydration with a dummy manifest
    dummy_manifest = {
        "manifest_id": "M-FUTURE-001",
        "project_id": "future_project_x",
        "pipeline_steps": [{
            "name": "future_solve",
            "requires": [],
            "produces": ["result.log"],
            "timeout_hours": 1,
            "target_repo": "nomad/future-worker"
        }]
    }
    
    # Trigger Hydration logic [cite: 204]
    state.hydrate_manifest(dummy_manifest)
    
    assert state.project_id == "future_project_x"
    assert state.manifest_data["manifest_id"] == "M-FUTURE-001"
    print("✅ Dummy Disc Test Passed: Engine is domain-agnostic.")

def test_conflict_simulation_hard_halt(tmp_path):
    """
    Verification: Hard-Halt Mandate.
    Ensures corrupted schema/manifest triggers a crash rather than a default.
    """
    config_path = tmp_path / "active_disk.json"
    # Malformed JSON to simulate corruption
    config_path.write_text("{ 'project_id': 'corrupt' ") 

    # Engine must Hard-Halt during mounting [cite: 314]
    with pytest.raises(RuntimeError) as excinfo:
        OrchestrationState(str(config_path), "/tmp", "/tmp/ledger.json")
    
    assert "Configuration Breach" in str(excinfo.value)
    print("✅ Conflict Simulation Passed: Engine correctly performed a Hard-Halt.")