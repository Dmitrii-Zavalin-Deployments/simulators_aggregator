# tests/behavior/test_forensic_discovery.py

import json
import pytest
from src.core.state_engine import OrchestrationState
from src.core.constants import OrchestrationStatus

def test_gap_finder_transition_logic(tmp_path):
    """
    CONSTITUTION CHECK: Phase B (2) - The Forensic Discovery Gate.
    Verifies that the engine transitions a step to PENDING when physical 
    requirements (inputs) are detected on disk.
    """
    # 1. SETUP: Seed Environment
    config_file = tmp_path / "disk.json"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    # Active Disk identity
    project_id = "GAP-TEST"
    config_file.write_text(json.dumps({
        "project_id": project_id,
        "manifest_url": "http://mock-manifest.com"
    }), encoding="utf-8")

    state = OrchestrationState(str(config_file), str(data_dir), str(tmp_path/"ledger.json"))

    # 2. DEFINE VALID MANIFEST: Physics Step
    # Must include 'project_id' and 'target_repo' to pass hydration gates
    manifest = {
        "manifest_id": "M-NAV-01",
        "project_id": project_id,
        "pipeline_steps": [{
            "name": "navier_stokes_solver",
            "requires": ["geometry.msh"],
            "produces": ["results.zip"],
            "target_repo": "nomad/fluid-worker",
            "timeout_hours": 1
        }]
    }
    state.hydrate_manifest(manifest)

    # 3. SCENARIO: Requirement Satisfied -> Transition to PENDING
    # Creating the 'requires' file on the physical disk
    (data_dir / "geometry.msh").write_text("Mock mesh data for simulation")
    
    # Starting state is WAITING
    ledger = {"navier_stokes_solver": {"status": OrchestrationStatus.WAITING.value}}
    
    # ACTION: Forensic reconciliation
    state.reconcile_and_heal(ledger)
    
    # VERIFICATION: Inputs present + outputs missing = PENDING (Ready to Fire)
    assert ledger["navier_stokes_solver"]["status"] == OrchestrationStatus.PENDING.value
    print("✅ Gap Finder Verified: Requirement presence triggered PENDING state.")

def test_forensic_completion_gate(tmp_path):
    """
    CONSTITUTION CHECK: Phase B (2) - Cycle Completion Gate.
    Verifies that the presence of 'produces' artifacts on disk marks 
    the step as COMPLETED, regardless of current ledger status.
    """
    # 1. SETUP
    config_file = tmp_path / "disk.json"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    project_id = "COMP-TEST"
    config_file.write_text(json.dumps({
        "project_id": project_id, 
        "manifest_url": "url"
    }), encoding="utf-8")
    
    state = OrchestrationState(str(config_file), str(data_dir), str(tmp_path/"ledger.json"))
    
    # 2. HYDRATION: Defining a task that produces a specific artifact
    state.hydrate_manifest({
        "manifest_id": "M-COMP",
        "project_id": project_id,
        "pipeline_steps": [{
            "name": "task_a", 
            "requires": [], 
            "produces": ["results.zip"],
            "target_repo": "nomad/completion-worker",
            "timeout_hours": 1
        }]
    })

    # 3. SCENARIO: Output artifact appears on disk
    (data_dir / "results.zip").write_text("Final simulation results artifact")
    
    # Ledger thinks we are still PENDING
    ledger = {"task_a": {"status": OrchestrationStatus.PENDING.value}}
    
    # ACTION: Forensic reconciliation
    state.reconcile_and_heal(ledger)
    
    # VERIFICATION: Presence of output triggers COMPLETED (Closing the loop)
    assert ledger["task_a"]["status"] == OrchestrationStatus.COMPLETED.value
    print("✅ Completion Gate Verified: Artifact presence triggered COMPLETED state.")

def test_id_mismatch_hard_halt(tmp_path):
    """
    CONSTITUTION CHECK: Phase B (6) - Identity Handshake.
    Verifies that hydration triggers a Hard-Halt if IDs do not align.
    """
    config_file = tmp_path / "disk.json"
    config_file.write_text(json.dumps({"project_id": "OWNER-A", "manifest_url": "url"}))
    
    state = OrchestrationState(str(config_file), str(tmp_path), str(tmp_path/"ledger.json"))
    
    # Manifest belongs to OWNER-B
    mismatched_manifest = {"project_id": "OWNER-B", "manifest_id": "M-B", "pipeline_steps": []}
    
    with pytest.raises(RuntimeError, match="CRITICAL: Hard-Halt"):
        state.hydrate_manifest(mismatched_manifest)
    
    print("✅ Identity Handshake: Hard-Halt confirmed for project mismatch.")