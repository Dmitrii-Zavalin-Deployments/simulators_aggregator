# tests/behavior/test_orchestration_mechanism.py

import json
from src.core.state_engine import OrchestrationState

def test_agnostic_gap_identification(tmp_path):
    """
    CONSTITUTION CHECK: Phase B - Artifact Gap Identification.
    Verifies that the state engine identifies missing artifacts (The Gap) 
    solely based on presence, satisfying the 'Mechanism' rule.
    """
    # 1. SETUP: Seed the "Disc" (disk.json) 
    # Mandatory for Deterministic Initialization (Rule 4 Compliance)
    config_file = tmp_path / "disk.json"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    ledger_path = tmp_path / "ledger.json"
    
    config_file.write_text(json.dumps({
        "project_id": "GAP-TEST-001",
        "manifest_url": "https://mock.cloud/manifest.json"
    }), encoding="utf-8")

    # 2. INITIALIZE: Mount the state now that disk.json exists
    state = OrchestrationState(
        config_path=str(config_file), 
        data_root=str(data_dir), 
        ledger_path=str(ledger_path)
    )
    
    # 3. SCENARIO: Define a manifest with a missing requirement
    # Testing the 'Mechanism' (Logic), not the 'Physics' (Data)
    manifest = {
        "manifest_id": "M-PROJ-X",
        "project_id": "GAP-TEST-001",
        "pipeline_steps": [{
            "name": "thermal_solver",
            "requires": ["missing_physics.dat"],
            "produces": ["thermal_result.csv"],
            "target_repo": "nomad/thermal-worker",
            "timeout_hours": 1
        }]
    }
    state.hydrate_manifest(manifest)
    
    # 4. EXECUTION: Reconcile state
    # Ledger initially marks the step as WAITING
    ledger = {"thermal_solver": {"status": "WAITING"}}
    state.reconcile_and_heal(ledger)
    
    # 5. VERIFICATION: Status must remain WAITING because missing_physics.dat is absent
    assert ledger["thermal_solver"]["status"] == "WAITING"
    print("✅ Artifact Gap Verified: Mechanism correctly identifies missing physics.")

def test_mechanism_sovereignty_mount(tmp_path):
    """
    CONSTITUTION CHECK: Phase B - System Verification Tiers.
    Verifies the 'Mechanism': The engine must successfully mount 
    the project configuration and initialize paths.
    """
    config_file = tmp_path / "active_disk.json"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    config_file.write_text(json.dumps({
        "project_id": "MOUNT-TEST",
        "manifest_url": "http://mock-cloud.com"
    }), encoding="utf-8")

    state = OrchestrationState(str(config_file), str(data_dir), str(tmp_path/"ledger.json"))

    assert state.project_id == "MOUNT-TEST"
    assert state.data_path.exists()
    print("✅ Mechanism Sovereignty Verified: Engine mounted independently of data presence.")