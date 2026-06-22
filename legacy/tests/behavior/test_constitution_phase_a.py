# tests/behavior/test_constitution_phase_a.py

import pytest
import json
from src.core.state_engine import OrchestrationState
from src.core.constants import OrchestrationStatus

def test_deterministic_idempotency_logic_gate(tmp_path):
    """
    CONSTITUTION CHECK: Phase A - Deterministic Idempotency Rule.
    Verifies that status transitions are driven SOLELY by physical artifact presence.
    """
    # 1. Setup Mock Node
    config_path = tmp_path / "active_disk.json"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    ledger_path = tmp_path / "ledger.json"
    
    config_path.write_text(json.dumps({
        "project_id": "TEST-PROJ",
        "manifest_url": "http://dummy.com"
    }))

    # 2. Initialize State (The Sovereign Logic Gate)
    state = OrchestrationState(str(config_path), str(data_dir), str(ledger_path))
    
    # Define a step: requires 'input.csv', produces 'output.csv'
    manifest = {
        "manifest_id": "M-001",
        "project_id": "TEST-PROJ",
        "pipeline_steps": [{
            "name": "step_one",
            "requires": ["input.csv"],
            "produces": ["output.csv"],
            "timeout_hours": 1,
            "target_repo": "org/repo"
        }]
    }
    state.manifest_data = manifest # Manual hydration for logic test
    
    # Initial Ledger: Step is WAITING
    ledger = {"step_one": {"status": OrchestrationStatus.WAITING.value}}

    # TEST A: Inputs Missing -> Remain WAITING
    state.reconcile_and_heal(ledger)
    assert ledger["step_one"]["status"] == OrchestrationStatus.WAITING.value

    # TEST B: Inputs Exist -> Transition to PENDING (Ready for Dispatch)
    (data_dir / "input.csv").write_text("data")
    state.reconcile_and_heal(ledger)
    assert ledger["step_one"]["status"] == OrchestrationStatus.PENDING.value

    # TEST C: Outputs Exist -> Transition to COMPLETED (Idempotency)
    (data_dir / "output.csv").write_text("result")
    state.reconcile_and_heal(ledger)
    assert ledger["step_one"]["status"] == OrchestrationStatus.COMPLETED.value

def test_single_slot_rule_mounting_failure(tmp_path):
    """
    CONSTITUTION CHECK: Phase A - The Mounting Protocol.
    Verifies the Engine Hard-Halts if the 'Slot' (active_disk.json) is corrupt.
    """
    config_path = tmp_path / "active_disk.json"
    config_path.write_text("NOT-JSON-CONTENT") # Corrupt the slot
    
    with pytest.raises(RuntimeError, match="Mounting Failed"):
        OrchestrationState(str(config_path), str(tmp_path), str(tmp_path / "ledger.json"))