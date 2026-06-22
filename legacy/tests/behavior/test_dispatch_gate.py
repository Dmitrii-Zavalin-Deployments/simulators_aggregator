# tests/behavior/test_dispatch_gate.py

from src.core.state_engine import OrchestrationState
from src.core.constants import OrchestrationStatus

def test_dispatch_gate_logic(tmp_path):
    """
    CONSTITUTION CHECK: Phase A (3) - The "Gate" Logic.
    Verifies that the engine only permits dispatch (PENDING status) 
    when the 'Artifacts_In' are present and 'Artifacts_Out' are absent.
    """
    # 1. Setup Mock Workspace
    config_path = tmp_path / "active_disk.json"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    ledger_path = tmp_path / "ledger.json"
    
    import json
    config_path.write_text(json.dumps({
        "project_id": "GATE-TEST",
        "manifest_url": "http://mock.com"
    }))

    # 2. Define Step with Dependencies
    manifest = {
        "manifest_id": "M-LOGIC",
        "project_id": "GATE-TEST",
        "pipeline_steps": [{
            "name": "worker_alpha",
            "requires": ["input.csv"],
            "produces": ["output.zip"],
            "timeout_hours": 1,
            "target_repo": "nomad/worker-alpha"
        }]
    }

    state = OrchestrationState(str(config_path), str(data_dir), str(ledger_path))
    state.manifest_data = manifest
    
    # Initial Ledger state
    ledger = {"worker_alpha": {"status": OrchestrationStatus.WAITING.value}}

    # TEST 1: Gate Closed (Missing Input)
    state.reconcile_and_heal(ledger)
    assert ledger["worker_alpha"]["status"] == OrchestrationStatus.WAITING.value
    assert state.get_ready_steps(ledger) is None

    # TEST 2: Gate Open (Input Present, Output Missing)
    (data_dir / "input.csv").write_text("data")
    state.reconcile_and_heal(ledger)
    assert ledger["worker_alpha"]["status"] == OrchestrationStatus.PENDING.value
    
    ready_steps = state.get_ready_steps(ledger)
    assert len(ready_steps) == 1
    assert ready_steps[0]["name"] == "worker_alpha"

    # TEST 3: Double-Spend Prevention (Output now exists)
    (data_dir / "output.zip").write_text("result")
    state.reconcile_and_heal(ledger)
    assert ledger["worker_alpha"]["status"] == OrchestrationStatus.COMPLETED.value
    assert state.get_ready_steps(ledger) is None
    print("✅ Dispatch Gate Protocol Verified: No redundant dispatches triggered.")