# tests/core/test_state_engine.py

import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch
from src.core.state_engine import OrchestrationState
from src.core.constants import OrchestrationStatus, SystemPaths

class TestOrchestrationStatePhysical:

    @pytest.fixture
    def state_setup(self, tmp_path, monkeypatch):
        """Creates the physical environment for State Engine testing."""
        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"
        schema_dir = tmp_path / "schema"
        
        # Fixed E701: Expanded loop for linter compliance
        for d in [config_dir, data_dir, schema_dir]:
            d.mkdir()

        # Patch SystemPaths to use our tmp directories
        monkeypatch.setattr("src.core.constants.SystemPaths.SCHEMA_DIR", str(schema_dir))
        
        config_path = config_dir / "active_disk.json"
        config_path.write_text(json.dumps({
            "project_id": "TEST-PROJ",
            "manifest_url": "http://dummy.com"
        }))

        schema_file = schema_dir / SystemPaths.MANIFEST_SCHEMA
        schema_file.write_text(json.dumps({
            "type": "object", 
            "required": ["project_id", "manifest_id"]
        }))

        ledger_path = config_dir / "ledger.json"
        
        return {
            "config": str(config_path),
            "data": str(data_dir),
            "ledger": str(ledger_path),
            "schema_dir": schema_dir
        }

    def test_init_creates_missing_data_path(self, state_setup):
        """Line 35-37: Verify directory creation if data_root doesn't exist."""
        new_data_path = Path(state_setup["data"]) / "nested_new_dir"
        assert not new_data_path.exists()
        
        OrchestrationState(state_setup["config"], str(new_data_path), state_setup["ledger"])
        assert new_data_path.exists()

    def test_is_job_stale_with_none_trigger(self, state_setup):
        """Line 84-86: Verify jobs with no trigger history are not considered stale."""
        state = OrchestrationState(state_setup["config"], state_setup["data"], state_setup["ledger"])
        ledger = {"job1": {"last_triggered": None, "timeout_hours": 1}}
        assert state._is_job_stale("job1", ledger) is False

    def test_save_ledger_persistence_error(self, state_setup):
        """Line 112-115: Catch and log exceptions during ledger write."""
        state = OrchestrationState(state_setup["config"], state_setup["data"], state_setup["ledger"])
        
        with patch("src.core.state_engine.logger") as mock_logger:
            # Fixed: Trigger OSError by pointing ledger path to an existing directory
            state.ledger_path = Path(state_setup["data"]) 
            state.save_ledger({})
            
            # Verify the log was called with the correct prefix
            args, _ = mock_logger.error.call_args
            assert "❌ Persistence Error" in args[0]

    def test_reconcile_without_hydration_fails(self, state_setup):
        """Line 121-123: Guard against scanning before hydration."""
        state = OrchestrationState(state_setup["config"], state_setup["data"], state_setup["ledger"])
        with pytest.raises(RuntimeError, match="Scan attempted without Manifest Hydration"):
            state.reconcile_and_heal({})

    def test_transition_matrix_edge_cases(self, state_setup):
        """Covers Lines 146-148, 157-159, and 161-166 (Transitions)."""
        state = OrchestrationState(state_setup["config"], state_setup["data"], state_setup["ledger"])
        
        # 1. Hydrate manifest with a complex step
        state.hydrate_manifest({
            "project_id": "TEST-PROJ",
            "manifest_id": "M1",
            "pipeline_steps": [{
                "name": "step_alpha",
                "requires": ["in.txt"],
                "produces": ["out.txt"]
            }]
        })

        # --- CASE 1: Input Loss (PENDING -> WAITING) ---
        ledger = {"step_alpha": {"status": OrchestrationStatus.PENDING.value}}
        state.reconcile_and_heal(ledger)
        assert ledger["step_alpha"]["status"] == OrchestrationStatus.WAITING.value

        # --- CASE 2: Artifact Drift (COMPLETED -> WAITING) ---
        ledger = {"step_alpha": {"status": OrchestrationStatus.COMPLETED.value}}
        state.reconcile_and_heal(ledger)
        assert ledger["step_alpha"]["status"] == OrchestrationStatus.WAITING.value

        # --- CASE 3: FAILED Recovery (FAILED -> PENDING) ---
        Path(state_setup["data"], "in.txt").write_text("data")
        ledger = {"step_alpha": {"status": OrchestrationStatus.FAILED.value}}
        state.reconcile_and_heal(ledger)
        assert ledger["step_alpha"]["status"] == OrchestrationStatus.PENDING.value

        # --- CASE 4: FAILED Recovery (FAILED -> WAITING) ---
        os.remove(Path(state_setup["data"], "in.txt"))
        ledger = {"step_alpha": {"status": OrchestrationStatus.FAILED.value}}
        state.reconcile_and_heal(ledger)
        assert ledger["step_alpha"]["status"] == OrchestrationStatus.WAITING.value