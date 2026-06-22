# tests/behavior/test_production_dispatch.py

import json
from src.core.state_engine import OrchestrationState
from src.core.constants import OrchestrationStatus

def test_production_handshake_alignment(tmp_path):
    """
    CONSTITUTION CHECK: Phase B (3) - Real-World Integration Gate.
    Verifies that the engine correctly maps a pipeline step to its 
    production 'target_repo' and marks it as PENDING for dispatch.
    """
    # 1. SETUP: Production-like Environment
    config_file = tmp_path / "disk.json"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    ledger_path = tmp_path / "ledger.json"
    
    project_id = "NAVIER-STOKES-PROD-001"
    config_file.write_text(json.dumps({
        "project_id": project_id,
        "manifest_url": "https://github.com/nomad/physics/manifest.json"
    }), encoding="utf-8")

    state = OrchestrationState(str(config_file), str(data_dir), str(ledger_path))

    # 2. DEFINE PRODUCTION MANIFEST
    target_solver = "navier-stokes-solver"
    manifest = {
        "manifest_id": "M-PROD-ALPHA",
        "project_id": project_id,
        "pipeline_steps": [{
            "name": "fluid_dynamics_solve",
            "requires": ["geometry.msh"],
            "produces": ["flow_results.zip"],
            "target_repo": target_solver,
            "timeout_hours": 24
        }]
    }
    state.hydrate_manifest(manifest)

    # 3. ACTION: Satisfy Physics Requirement (Simulating geometry upload)
    (data_dir / "geometry.msh").write_text("Physical Mesh Data")
    
    # Ledger starts at WAITING
    ledger = {"fluid_dynamics_solve": {"status": OrchestrationStatus.WAITING.value}}
    
    # 4. EXECUTION: The Logic Gate Reconciles
    state.reconcile_and_heal(ledger)

    # 5. VERIFICATION: Handshake Readiness
    # Verify the state moved to PENDING (Ready for Github Dispatch)
    assert ledger["fluid_dynamics_solve"]["status"] == OrchestrationStatus.PENDING.value
    
    # Verify the target mapping is accurate for the external trigger
    step_metadata = state.manifest_data["pipeline_steps"][0]
    assert step_metadata["target_repo"] == target_solver
    assert state.project_id == project_id
    
    print(f"✅ Production Handshake Verified: {project_id} ready to dispatch to {target_solver}")