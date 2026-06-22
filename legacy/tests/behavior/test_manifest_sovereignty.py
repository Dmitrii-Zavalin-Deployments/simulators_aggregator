# tests/behavior/test_manifest_sovereignty.py

import pytest
import json
from unittest.mock import patch
from src.core.state_engine import OrchestrationState
from src.core.constants import SystemPaths

def test_schema_sovereignty_hard_halt(tmp_path):
    """
    CONSTITUTION CHECK: Phase A - Schema Sovereignty.
    Verifies that a malformed remote manifest triggers a Hard-Halt 
    to prevent "Logic Drift" or corrupted simulation runs.
    """
    # 1. Setup Mock Environment
    config_dir = tmp_path / "config"
    schema_dir = tmp_path / "schema"
    config_dir.mkdir()
    schema_dir.mkdir()
    
    # Create the local 'Slot' (active_disk.json)
    active_disk = config_dir / SystemPaths.ACTIVE_DISK
    active_disk.write_text(json.dumps({
        "project_id": "HALT-TEST",
        "manifest_url": "http://mock-manifest.com"
    }))
    
    # Create a dummy schema that requires 'project_id'
    manifest_schema = schema_dir / SystemPaths.MANIFEST_SCHEMA
    manifest_schema.write_text(json.dumps({
        "type": "object",
        "required": ["project_id"],
        "properties": {"project_id": {"type": "string"}}
    }))

    # 2. Mock a Corrupt Remote Manifest (Missing required project_id)
    corrupt_manifest = {"manifest_id": "M-001"} # Missing 'project_id'

    # 3. Patch SystemPaths to use our temp directories
    with patch("src.core.state_engine.SystemPaths.SCHEMA_DIR", str(schema_dir)):
        
        # Initialize State (The Sovereign Logic Gate)
        state = OrchestrationState(str(active_disk), str(tmp_path), str(tmp_path/"ledger.json"))
        
        # 4. Execution: Hydration must Fail with a Hard-Halt [cite: 316]
        with pytest.raises(RuntimeError, match="CRITICAL: Hard-Halt"):
            state.hydrate_manifest(corrupt_manifest)

def test_mounting_zero_knowledge_initialization(tmp_path):
    """
    CONSTITUTION CHECK: Phase A - Zero-Knowledge Protocol.
    Confirms the Engine cannot initialize project state until the disk is mounted.
    """
    config_path = tmp_path / "active_disk.json"
    # File does not exist yet (No disk in slot)
    
    with pytest.raises(RuntimeError, match="Mounting Failed"):
        OrchestrationState(str(config_path), str(tmp_path), str(tmp_path/"ledger.json"))