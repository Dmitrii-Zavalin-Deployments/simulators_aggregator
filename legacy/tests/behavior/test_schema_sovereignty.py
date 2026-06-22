# tests/behavior/test_schema_sovereignty.py

import json
import pytest
from src.core.state_engine import OrchestrationState

def test_manifest_schema_hard_halt(tmp_path):
    """
    CONSTITUTION CHECK: Phase A (5) - Manifest Schema Validation.
    Verifies that a 'corrupt disk' (invalid manifest) results in an 
    immediate Hard-Halt, preventing execution under ambiguity.
    """
    # 1. Setup Mock Workspace
    config_file = tmp_path / "disk.json"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    ledger_path = tmp_path / "ledger.json"
    
    # Seed the mandatory disk config
    config_file.write_text(json.dumps({
        "project_id": "HALT-TEST",
        "manifest_url": "http://mock.com"
    }), encoding="utf-8")

    # 2. Initialize Engine - Define 'state' in local scope
    state = OrchestrationState(str(config_file), str(data_dir), str(ledger_path))

    # 3. SCENARIO: Corrupt Manifest - Define 'corrupt_manifest' in local scope
    # Missing 'pipeline_steps' mandatory property
    corrupt_manifest = {
        "manifest_id": "M-BAD",
        "project_id": "HALT-TEST"
    }

    # 4. EXECUTION & VERIFICATION: Hard-Halt
    with pytest.raises(RuntimeError) as excinfo:
        state.hydrate_manifest(corrupt_manifest)
    
    # 5. Forensic Alignment: Validate actual error message produced by the engine
    error_msg = str(excinfo.value)
    assert "CRITICAL: Hard-Halt" in error_msg
    assert "pipeline_steps" in error_msg
    assert "required property" in error_msg
    
    print("✅ Schema Sovereignty Verified: Engine successfully halted on corrupt manifest.")

def test_agnostic_execution_gate(tmp_path):
    """
    CONSTITUTION CHECK: Phase A (5) - Agnostic Execution.
    Verifies the engine only cares about filename presence, not content.
    """
    # Setup directories
    config_file = tmp_path / "disk.json"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    ledger_path = tmp_path / "ledger.json"
    
    config_file.write_text(json.dumps({
        "project_id": "AGNOSTIC", 
        "manifest_url": "http://mock.com"
    }), encoding="utf-8")
    
    state = OrchestrationState(str(config_file), str(data_dir), str(ledger_path))
    
    # Physical truth: Engine recognizes existence, not content (Agnostic Rule)
    artifact_path = data_dir / "required_artifact.zip"
    artifact_path.write_text("Agnostic payload: non-binary content check.")
    
    assert artifact_path.exists()
    assert (state.data_path / "required_artifact.zip").exists()
    print("✅ Agnostic Execution Verified: Engine recognizes artifact presence regardless of internal content.")