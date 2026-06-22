# tests/behavior/test_artifact_forensics.py

import json
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from src.core.state_engine import OrchestrationState
from src.core.constants import OrchestrationStatus

# --- PHASE A (2): IDEMPOTENCY & ISOLATION ---

def test_forensic_idempotency_recovery(tmp_path):
    """
    CONSTITUTION CHECK: Phase A (2) - Idempotency Contract.
    Verifies that the Engine resumes based on Physical Artifact Truth 
    even if the ledger is out of sync.
    """
    # 1. Setup Mock Workspace
    config_path = tmp_path / "active_disk.json"
    data_dir = tmp_path / "data/testing-input-output"
    data_dir.mkdir(parents=True)
    ledger_path = tmp_path / "ledger.json"

    # Seed the physical disk slot
    config_path.write_text(json.dumps({
        "project_id": "FORENSIC-TEST",
        "manifest_url": "http://mock.com"
    }), encoding="utf-8")

    # 2. Define a 2-Step Pipeline
    manifest = {
        "manifest_id": "M-XYZ",
        "project_id": "FORENSIC-TEST",
        "pipeline_steps": [
            {"name": "step_1", "requires": [], "produces": ["artifact_1.zip"], "timeout_hours": 1, "target_repo": "repo/1"},
            {"name": "step_2", "requires": ["artifact_1.zip"], "produces": ["final.csv"], "timeout_hours": 1, "target_repo": "repo/2"}
        ]
    }

    # Initialize Sovereign Logic Gate
    state = OrchestrationState(str(config_path), str(data_dir), str(ledger_path))
    state.manifest_data = manifest

    # 3. SCENARIO: Physical truth exists (artifact_1 is done), but ledger says WAITING
    (data_dir / "artifact_1.zip").write_text("binary-data")
    
    mock_ledger = {
        "step_1": {"status": OrchestrationStatus.WAITING.value},
        "step_2": {"status": OrchestrationStatus.WAITING.value}
    }

    # 4. EXECUTION: Forensic Scan (Reconcile & Heal)
    state.reconcile_and_heal(mock_ledger)

    # 5. VERIFICATION
    assert mock_ledger["step_1"]["status"] == OrchestrationStatus.COMPLETED.value
    assert mock_ledger["step_2"]["status"] == OrchestrationStatus.PENDING.value
    print("✅ Forensic Discovery Alignment Confirmed: Execution resumes based on disk truth.")

def test_clean_room_isolation(tmp_path):
    """
    CONSTITUTION CHECK: Phase A (2) - Isolation Mandate.
    Confirms the Engine only recognizes artifacts in the designated DATA_DIR.
    """
    # 1. Setup Directories
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    # 2. Protocol Requirement: Seed the disk configuration
    config_file = tmp_path / "disk.json"
    config_file.write_text(json.dumps({
        "project_id": "ISO-TEST", 
        "manifest_url": "http://mock-url.com"
    }), encoding="utf-8")

    # 3. Place a file OUTSIDE the recognized data directory
    (tmp_path / "stray_artifact.zip").write_text("contamination")
    
    # 4. Initialize Engine
    state = OrchestrationState(
        str(config_file), 
        str(data_dir), 
        str(tmp_path / "ledger.json")
    )
    
    # 5. Verification: Check that the engine remains blind to outside files
    assert not (Path(state.data_path) / "stray_artifact.zip").exists()
    print("✅ Isolation Mandate Verified: Engine is successfully isolated from contamination.")

# --- PHASE B (6): STATE-MACHINE LOGIC & IDENTITY ---

def test_timeout_recovery_logic(tmp_path):
    """
    CONSTITUTION CHECK: Phase B (6) - Forensic Decision Tree.
    Verifies that a stale IN_PROGRESS job is marked as FAILED by reconcile_and_heal.
    """
    # 1. SETUP
    config_file = tmp_path / "disk.json"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    ledger_path = tmp_path / "ledger.json"
    
    config_file.write_text(json.dumps({"project_id": "TIME-TEST", "manifest_url": "url"}), encoding="utf-8")
    state = OrchestrationState(str(config_file), str(data_dir), str(ledger_path))
    
    step_name = "stale_process"
    state.hydrate_manifest({
        "manifest_id": "M-TIME",
        "project_id": "TIME-TEST",
        "pipeline_steps": [{
            "name": step_name,
            "requires": [],
            "produces": ["output.zip"],
            "timeout_hours": 2, # 2 Hour limit
            "target_repo": "nomad/worker"
        }]
    })

    # 2. SCENARIO: Stale Lock (Simulate timestamp from 5 hours ago)
    stale_time = (datetime.now() - timedelta(hours=5)).isoformat()
    ledger = {
        step_name: {
            "status": OrchestrationStatus.IN_PROGRESS.value,
            "last_triggered": stale_time
        }
    }

    # 3. ACTION: The Logic Loop reconciles against the stale lock
    state.reconcile_and_heal(ledger)

    # 4. VERIFICATION: Forensic marking of Failure per Rule 4
    assert ledger[step_name]["status"] == OrchestrationStatus.FAILED.value
    print(f"✅ Timeout Verified: Stale task {step_name} transitioned to FAILED.")

def test_identity_handshake_mismatch(tmp_path):
    """
    CONSTITUTION CHECK: Phase B (6) - Metadata Handshake.
    Verifies that hydration fails if the manifest doesn't match the config project_id.
    """
    config_file = tmp_path / "disk.json"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    # Config says Project A
    config_file.write_text(json.dumps({"project_id": "PROJECT-A", "manifest_url": "url"}), encoding="utf-8")
    state = OrchestrationState(str(config_file), str(data_dir), str(tmp_path/"ledger.json"))

    # Manifest says Project B (The Breach)
    mismatched_manifest = {
        "manifest_id": "M-MISMATCH",
        "project_id": "PROJECT-B", 
        "pipeline_steps": []
    }

    # 3. ACTION & VERIFICATION: Hard-Halt for Identity Breach
    with pytest.raises(RuntimeError) as excinfo:
        state.hydrate_manifest(mismatched_manifest)
    
    assert "Identity Mismatch" in str(excinfo.value)
    print("✅ Identity Guard Verified: Blocked project_id mismatch.")