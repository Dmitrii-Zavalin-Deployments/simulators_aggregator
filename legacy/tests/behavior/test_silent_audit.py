# tests/behavior/test_silent_audit.py

import json
from src.core.state_engine import OrchestrationState
from src.core.constants import OrchestrationStatus

def test_atomic_persistence_audit(tmp_path):
    """
    CONSTITUTION CHECK: Phase B (4) - The Silent Operator Audit Gate.
    Verifies Rule 4: Atomic Persistence. The ledger must be updated on disk 
    immediately following a state reconciliation to prevent state loss.
    """
    # 1. SETUP: Environment
    config_file = tmp_path / "disk.json"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    ledger_path = tmp_path / "orchestration_ledger.json" # The Audit Target
    
    project_id = "AUDIT-PROJ-01"
    config_file.write_text(json.dumps({
        "project_id": project_id,
        "manifest_url": "http://mock.com"
    }), encoding="utf-8")

    state = OrchestrationState(str(config_file), str(data_dir), str(ledger_path))
    
    step_name = "audit_step"
    state.hydrate_manifest({
        "manifest_id": "M-AUDIT",
        "project_id": project_id,
        "pipeline_steps": [{
            "name": step_name,
            "requires": ["input.txt"],
            "produces": ["output.txt"],
            "target_repo": "nomad/audit-worker",
            "timeout_hours": 1
        }]
    })

    # 2. INITIAL STATE: Define a WAITING ledger in memory
    initial_ledger = {step_name: {"status": OrchestrationStatus.WAITING.value}}
    
    # 3. ACTION: Satisfy physics (create input) and trigger Logic Gate
    (data_dir / "input.txt").write_text("Triggering silent audit...")
    
    # This call triggers the internal state change and the save to ledger_path
    state.reconcile_and_heal(initial_ledger)

    # 4. VERIFICATION: Forensic Disk Audit
    assert ledger_path.exists(), "❌ FAIL: Ledger was not physically persisted to disk."
    
    with open(ledger_path, 'r', encoding="utf-8") as f:
        disk_data = json.load(f)
        
    # Check for 'steps' wrapper alignment (Standardizing nomadic data structures)
    actual_ledger = disk_data.get("steps", disk_data)
    
    assert step_name in actual_ledger, f"❌ KeyError: {step_name} missing from disk."
    assert actual_ledger[step_name]["status"] == OrchestrationStatus.PENDING.value
    
    print("✅ Audit Gate Verified: Ledger on disk reflects PENDING state.")

def test_audit_traceability_sequence(tmp_path):
    """
    CONSTITUTION CHECK: Phase B (4) - Traceability.
    Verifies that the COMPLETED state transition is also atomically tracked.
    """
    config_file = tmp_path / "disk.json"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    ledger_path = tmp_path / "orchestration_ledger.json"
    
    project_id = "TRACE-01"
    config_file.write_text(json.dumps({"project_id": project_id, "manifest_url": "url"}), encoding="utf-8")
    state = OrchestrationState(str(config_file), str(data_dir), str(ledger_path))
    
    step_name = "step_x"
    state.hydrate_manifest({
        "manifest_id": "M-TRACE",
        "project_id": project_id,
        "pipeline_steps": [{
            "name": step_name, 
            "requires": [], 
            "produces": ["final.zip"], 
            "target_repo": "nomad/trace-worker",
            "timeout_hours": 1
        }]
    })

    # Scenario: Physical artifact appears, marking the end of a cycle
    (data_dir / "final.zip").write_text("End of nomadic run")
    ledger = {step_name: {"status": OrchestrationStatus.PENDING.value}}
    
    # ACTION: Reconcile logic with physical reality
    state.reconcile_and_heal(ledger)
    
    # VERIFICATION: Verify Disk Integrity for the COMPLETED status
    with open(ledger_path, 'r', encoding="utf-8") as f:
        disk_data = json.load(f)
    
    actual_ledger = disk_data.get("steps", disk_data)
    assert actual_ledger[step_name]["status"] == OrchestrationStatus.COMPLETED.value
    print("✅ Traceability Verified: COMPLETED state persisted to nomadic ledger.")