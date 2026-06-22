# tests/behavior/test_boot_hydration.py

import json
import pytest
from src.core.bootloader import Bootloader
from src.core.state_engine import OrchestrationState

def test_bootloader_hydration_gate(tmp_path):
    """
    CONSTITUTION CHECK: Phase B (1) - Mounting & Hydration Gate.
    Verifies that the Bootloader can mount the 'Disc' and the State 
    can hydrate the manifest data accurately.
    """
    # 1. Setup Mock "Disc" (active_disk.json)
    config_file = tmp_path / "active_disk.json"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    ledger_path = tmp_path / "ledger.json"
    
    project_id = "NAVIER-STOKES-FLUIDS"
    config_file.write_text(json.dumps({
        "project_id": project_id,
        "manifest_url": "https://raw.githubusercontent.com/nomad/sim/main/manifest.json"
    }), encoding="utf-8")

    # 2. STEP 1: MOUNTING (The Ignition Phase)
    # Bootloader.mount returns an OrchestrationState instance
    state = Bootloader.mount(str(config_file), str(data_dir), str(ledger_path))
    
    assert isinstance(state, OrchestrationState)
    assert state.project_id == project_id
    assert state.manifest_data is None  # Should be empty before hydration

    # 3. STEP 2: HYDRATION (The Ingestion Phase)
    mock_manifest = {
        "manifest_id": "M-FLUID-001",
        "project_id": project_id,
        "pipeline_steps": [
            {
                "name": "flow_solver",
                "requires": ["initial_mesh.msh"],
                "produces": ["velocity_vectors.csv"],
                "target_repo": "navier-stokes-solver",
                "timeout_hours": 12
            }
        ]
    }
    
    # This call triggers the internal Identity Guard and Schema Sovereignty check
    state.hydrate_manifest(mock_manifest)

    # 4. FINAL VERIFICATION
    target = state.manifest_data['pipeline_steps'][0]['target_repo']
    assert target == "navier-stokes-solver"
    
    print(f"✅ Boot Hydration Verified: Project {project_id} mapped to {target}")


def test_identity_handshake_mismatch(tmp_path):
    """
    CONSTITUTION CHECK: Phase B (6) - Metadata Handshake (Identity Guard).
    Verifies that hydration triggers a Hard-Halt if the manifest project_id 
    does not match the disk project_id.
    """
    # 1. SETUP: Disk configured for PROJECT-ALPHA
    config_file = tmp_path / "active_disk.json"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    config_file.write_text(json.dumps({
        "project_id": "PROJECT-ALPHA",
        "manifest_url": "url"
    }), encoding="utf-8")
    
    state = OrchestrationState(str(config_file), str(data_dir), str(tmp_path/"ledger.json"))

    # 2. SCENARIO: Manifest arrives from PROJECT-BETA (The Breach)
    mismatched_manifest = {
        "manifest_id": "M-BETA-001",
        "project_id": "PROJECT-BETA", 
        "pipeline_steps": []
    }

    # 3. ACTION & VERIFICATION: Must raise RuntimeError with the Hard-Halt signature
    with pytest.raises(RuntimeError, match="CRITICAL: Hard-Halt"):
        state.hydrate_manifest(mismatched_manifest)
    
    print("✅ Identity Guard Verified: Blocked project_id mismatch with Hard-Halt signature.")