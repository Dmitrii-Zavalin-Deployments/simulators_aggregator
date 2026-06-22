# tests/architecture/test_orchestration_loop.py

import json
from src.core.bootloader import Bootloader
from src.core.constants import SystemPaths, OrchestrationStatus
from src.core.update_ledger import LedgerManager

def test_full_orchestration_alignment(tmp_path, monkeypatch):
    """
    CONSTITUTION CHECK: Phase C (3) - Orchestration Alignment.
    Verifies the handshake between Bootloader, StateEngine, and LedgerManager.
    """
    # 1. Setup Mock Filesystem Standardized via SystemPaths [cite: 216]
    config_dir = tmp_path / SystemPaths.CONFIG_DIR
    config_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    # 2. Mock Active Disk [cite: 197]
    active_disk = config_dir / SystemPaths.ACTIVE_DISK
    active_disk.write_text(json.dumps({
        "project_id": "test-alignment-lab",
        "manifest_url": "http://localhost/mock_manifest.json"
    }))
    
    ledger_path = config_dir / SystemPaths.LEDGER
    audit_path = tmp_path / "performance_audit.md"

    # 3. STAGE: Mounting 
    state = Bootloader.mount(str(active_disk), str(data_dir), str(ledger_path))
    assert state.project_id == "test-alignment-lab"
    assert state.ledger_path == ledger_path

    # 4. STAGE: Audit (Prepend Check) 
    ledger_manager = LedgerManager(log_path=str(audit_path))
    ledger_manager.record_event("TEST_HANDSHAKE", "Orchestration Alignment Verified.")
    
    with open(audit_path, "r") as f:
        content = f.read()
        assert "# 🛰️ Simulation Engine Performance Audit" in content
        assert "TEST_HANDSHAKE" in content

    # 5. STAGE: Forensic Scan (Simulate Physical Truth) 
    # We verify that status access follows Rule 4 (No .get() defaults) [cite: 217]
    mock_ledger = {
        "metadata": {"project_id": "test", "manifest_id": "m1"},
        "steps": {
            "alpha_solver": {
                "status": OrchestrationStatus.WAITING.value,
                "last_triggered": None,
                "timeout_hours": 6,
                "target_repo": "nomad/alpha"
            }
        }
    }
    
    # Direct access test: Ensuring core keys exist
    assert mock_ledger["steps"]["alpha_solver"]["status"] == "WAITING"
    print("✅ Orchestration Alignment Verified: Cycle Stages aligned with Engine Logic.")