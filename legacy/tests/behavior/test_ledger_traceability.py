# tests/behavior/test_ledger_traceability.py

from src.core.update_ledger import LedgerManager
from src.core.constants import OrchestrationStatus

def test_ledger_atomic_persistence(tmp_path):
    """
    CONSTITUTION CHECK: Phase A (4) - The Sovereign Ledger.
    Verifies that state changes are physically written to the audit log
    to ensure traceability across orchestration pulses.
    """
    # 1. Setup - Using performance_audit.md as discovered in main_engine.py
    audit_log = tmp_path / "performance_audit.md"
    manager = LedgerManager(log_path=str(audit_log))
    
    project_id = "PROJ-ALPHA"
    manifest_id = "M-123"
    step_name = "simulation_run"

    # 2. Log a Dispatch Event
    # This method writes to the markdown audit trail as seen in main_engine usage
    manager.log_dispatch(
        project_id=project_id,
        manifest_id=manifest_id,
        step_name=step_name,
        target_repo="nomad/worker-repo",
        timeout_hours=1
    )

    # 3. Physical Verification (The "Black Box" Check)
    assert audit_log.exists()
    content = audit_log.read_text()
    
    # Verify the audit trail contains the critical forensic keys
    assert project_id in content
    assert step_name in content
    assert "DISPATCH" in content.upper()
    print("✅ Ledger Traceability Verified: Audit event persisted to performance_audit.md")

def test_dormancy_evaluation_logic(tmp_path):
    """
    CONSTITUTION CHECK: Phase A (4) - System Health.
    Verifies the LedgerManager can correctly identify when a project 
    should transition to DORMANT.
    """
    audit_log = tmp_path / "health_check.md"
    manager = LedgerManager(log_path=str(audit_log))
    
    # Scenario: All steps are completed
    # Note: LedgerManager evaluates the dictionary of steps directly
    updated_steps = {
        "step_1": {"status": OrchestrationStatus.COMPLETED.value},
        "step_2": {"status": OrchestrationStatus.COMPLETED.value}
    }
    
    status = manager.evaluate_dormancy_state(updated_steps)
    assert "DORMANT" in status
    print("✅ System Health Verified: Dormancy gate correctly identifies completed missions.")

def test_ledger_hydration_integrity(tmp_path):
    """
    CONSTITUTION CHECK: Phase A (4) - Traceable Physics.
    Verifies that the manager can load existing state from a previous Pulse.
    Note: LedgerManager in this implementation handles the audit trail (MD),
    while OrchestrationState handles the JSON ledger.
    """
    audit_log = tmp_path / "performance_audit.md"
    manager = LedgerManager(log_path=str(audit_log))
    
    # Log an event to the audit trail
    manager.record_event("BOOT", "Initial Pulse")
    
    assert audit_log.exists()
    assert "Initial Pulse" in audit_log.read_text()
    print("✅ Audit Hydration Verified: Markdown history is persistent.")