# tests/core/test_bootloader.py

import pytest
import json
import responses
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.core.bootloader import Bootloader
from src.core.constants import SystemPaths, OrchestrationStatus

class TestBootloaderForensics:

    @pytest.fixture
    def mock_env(self, tmp_path, monkeypatch):
        """Sets up a physical mock environment for the Bootloader."""
        config_dir = tmp_path / "config"
        schema_dir = tmp_path / "schema"
        config_dir.mkdir()
        schema_dir.mkdir()

        # Patch system constants to point to tmp paths
        monkeypatch.setattr("src.core.constants.SystemPaths.CONFIG_DIR", str(config_dir))
        monkeypatch.setattr("src.core.constants.SystemPaths.SCHEMA_DIR", str(schema_dir))

        # Create dummy schemas required for Rule 4 validation
        (schema_dir / SystemPaths.ACTIVE_DISK_SCHEMA).write_text(json.dumps({"type": "object"}))
        (schema_dir / SystemPaths.MANIFEST_SCHEMA).write_text(json.dumps({"type": "object"}))

        return {"config": config_dir, "schema": schema_dir}

    def test_validate_integrity_failure(self, mock_env):
        """Line 30-35: Verify hard-halt on schema breach."""
        bad_data = {"unexpected": "field"}
        # Overwrite schema with one that requires a specific field to force failure
        schema_name = "test_schema.json"
        (mock_env["schema"] / schema_name).write_text(json.dumps({"required": ["id"]}))
        
        # FIX: Matching the actual exception string "CRITICAL: test_schema.json is corrupt..."
        with pytest.raises(RuntimeError, match=f"CRITICAL: {schema_name} is corrupt or invalid"):
            Bootloader._validate_integrity(bad_data, schema_name)

    def test_mount_dormancy_reset_oserror(self, mock_env):
        """Line 51-54: Catch OSError when failing to reset dormant flag."""
        dormant_flag = Path(SystemPaths.CONFIG_DIR) / SystemPaths.DORMANT_FLAG
        config_file = Path(mock_env["config"]) / "active.json"
        
        # Setup files: config is newer than dormant flag to trigger the reset attempt
        dormant_flag.write_text("STATUS: DORMANT", encoding="utf-8")
        config_file.write_text(json.dumps({"project_id": "P1"}), encoding="utf-8")
        
        # Force mtime alignment
        os.utime(config_file, (os.path.getatime(config_file), os.path.getmtime(dormant_flag) + 100))
        
        # Patch write_text specifically on the dormant_flag path to raise OSError
        with patch.object(Path, "write_text", side_effect=OSError("Disk Read Only")):
            with patch("src.core.bootloader.logger") as mock_logger:
                try:
                    Bootloader.mount(str(config_file), "/tmp/data", "/tmp/ledger.json")
                except Exception:
                    # OrchestrationState init might fail due to dummy paths; we focus on the log
                    pass
                mock_logger.error.assert_any_call("Failed to reset dormancy flag: Disk Read Only")

    @responses.activate
    def test_hydrate_project_pivot_reset(self, mock_env):
        """Line 85-122: Verify ledger reset when project_id or manifest_id shifts."""
        # 1. Setup local 'Active Disk' (Rule 0 Integrity)
        active_disk = Path(SystemPaths.CONFIG_DIR) / SystemPaths.ACTIVE_DISK
        active_disk.write_text(json.dumps({"project_id": "OLD_PROJ"}), encoding="utf-8")

        # 2. Setup existing Ledger with OLD_PROJ metadata
        ledger_path = mock_env["config"] / "ledger.json"
        ledger_path.write_text(json.dumps({
            "metadata": {"project_id": "OLD_PROJ", "manifest_id": "M1"},
            "steps": {"old_step": {"status": "COMPLETED"}}
        }), encoding="utf-8")

        # 3. Mock Remote Manifest with NEW_PROJ (Triggering the Pivot)
        manifest_url = "http://api.nomad.com/manifest"
        new_manifest = {
            "project_id": "NEW_PROJ",
            "manifest_id": "M2",
            "pipeline_steps": [
                {"name": "step1", "timeout_hours": 5, "target_repo": "repo1"}
            ]
        }
        responses.add(responses.GET, manifest_url, json=new_manifest, status=200)

        # 4. Mock State Engine
        mock_state = MagicMock()
        mock_state.manifest_url = manifest_url
        mock_state.ledger_path = str(ledger_path)
        mock_state.project_id = "OLD_PROJ"

        # Execution
        ledger_content = Bootloader.hydrate(mock_state)

        # Validation: Metadata must pivot and steps must be re-seeded
        assert ledger_content["metadata"]["project_id"] == "NEW_PROJ"
        assert "step1" in ledger_content["steps"]
        assert "old_step" not in ledger_content["steps"]
        assert ledger_content["steps"]["step1"]["status"] == OrchestrationStatus.WAITING.value
        
        # Verify Rule 1: Atomic Disk Persistence
        saved_ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        assert saved_ledger["metadata"]["project_id"] == "NEW_PROJ"

    def test_hydrate_critical_failure_catch(self, mock_env):
        """Line 130-133: Catch-all for hydration exceptions."""
        mock_state = MagicMock()
        # Non-existent path will trigger a file read error in step 1
        mock_state.ledger_path = "/non/existent/path/ledger.json"
        
        with pytest.raises(RuntimeError, match="CRITICAL: Hydration failure"):
            Bootloader.hydrate(mock_state)
    
    @responses.activate
    def test_hydrate_recovery_from_corruption(self, mock_env):
        """Covers Lines 92-93: Recovery from Corrupt JSON or Missing Keys."""
        # 1. Simulate a corrupted Ledger file (Invalid JSON)
        ledger_path = mock_env["config"] / "ledger.json"
        ledger_path.write_text("{ incomplete_json: ", encoding="utf-8")

        # 2. Setup mock manifest to allow re-seeding
        manifest_url = "http://api.nomad.com/manifest"
        responses.add(responses.GET, manifest_url, json={
            "project_id": "P1", "manifest_id": "M1", "pipeline_steps": []
        }, status=200)

        # 3. Setup Active Disk (local entry point)
        (Path(SystemPaths.CONFIG_DIR) / SystemPaths.ACTIVE_DISK).write_text(
            json.dumps({"project_id": "P1"}), encoding="utf-8"
        )

        mock_state = MagicMock()
        mock_state.manifest_url = manifest_url
        mock_state.ledger_path = str(ledger_path)

        # This should NOT raise an error; it should catch the JSONDecodeError and reset.
        ledger_content = Bootloader.hydrate(mock_state)
        
        assert ledger_content["metadata"]["project_id"] == "P1"
        # Verify the file was overwritten with valid data
        assert json.loads(ledger_path.read_text())["metadata"]["project_id"] == "P1"

    @responses.activate
    def test_hydrate_recovery_from_missing_metadata(self, mock_env):
        """Covers Lines 92-93: Recovery when JSON is valid but keys are missing."""
        ledger_path = mock_env["config"] / "ledger.json"
        # Valid JSON, but missing the "metadata" key required by Line 88
        ledger_path.write_text(json.dumps({"wrong_key": "data"}), encoding="utf-8")

        manifest_url = "http://api.nomad.com/manifest"
        responses.add(responses.GET, manifest_url, json={
            "project_id": "P1", "manifest_id": "M1", "pipeline_steps": []
        }, status=200)

        (Path(SystemPaths.CONFIG_DIR) / SystemPaths.ACTIVE_DISK).write_text(
            json.dumps({"project_id": "P1"}), encoding="utf-8"
        )

        mock_state = MagicMock()
        mock_state.manifest_url = manifest_url
        mock_state.ledger_path = str(ledger_path)

        # Execution should trigger the KeyError, catch it, and reset.
        ledger_content = Bootloader.hydrate(mock_state)
        assert "metadata" in ledger_content

    @responses.activate
    def test_hydrate_first_ignition_new_file(self, mock_env):
        """Covers Lines 94-96: Handles 'Cold Start' where ledger file does not exist."""
        # 1. Setup path for a file that does NOT exist
        ledger_path = mock_env["config"] / "brand_new_ledger.json"
        if ledger_path.exists():
            ledger_path.unlink()

        # 2. Mock Remote Manifest
        manifest_url = "http://api.nomad.com/manifest"
        new_manifest = {
            "project_id": "COLD_START_PROJ",
            "manifest_id": "M_INIT",
            "pipeline_steps": [
                {"name": "init_step", "timeout_hours": 1, "target_repo": "worker-repo"}
            ]
        }
        responses.add(responses.GET, manifest_url, json=new_manifest, status=200)

        # 3. Setup local 'Active Disk'
        (Path(SystemPaths.CONFIG_DIR) / SystemPaths.ACTIVE_DISK).write_text(
            json.dumps({"project_id": "COLD_START_PROJ"}), encoding="utf-8"
        )

        # 4. Execute Hydration
        mock_state = MagicMock()
        mock_state.manifest_url = manifest_url
        mock_state.ledger_path = str(ledger_path)
        
        ledger_content = Bootloader.hydrate(mock_state)

        # --- VALIDATION ---
        # Verify the 'else' block (Line 95) was triggered and should_reset became True
        assert ledger_content["metadata"]["project_id"] == "COLD_START_PROJ"
        assert "init_step" in ledger_content["steps"]
        
        # Verify Rule 1: The file was actually written to the empty disk location
        assert ledger_path.exists()
        saved_data = json.loads(ledger_path.read_text(encoding="utf-8"))
        assert saved_data["metadata"]["manifest_id"] == "M_INIT"