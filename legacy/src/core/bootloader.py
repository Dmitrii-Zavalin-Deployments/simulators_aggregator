# src/core/bootloader.py

import requests
import logging
import json
from pathlib import Path
from jsonschema import validate

# Internal Core Imports
from src.core.constants import SystemPaths, OrchestrationStatus
from src.core.state_engine import OrchestrationState

logger = logging.getLogger("Engine.Bootloader")

class Bootloader:
    """
    The Ignition System for the Nomadic Engine.
    Responsibility: Filesystem mounting, schema validation, and ledger synchronization.
    Compliance: Rule 0 (Integrity), Rule 1 (Clean Room), Rule 4 (Zero-Default).
    """

    @staticmethod
    def _validate_integrity(data: dict, schema_filename: str):
        """
        Rule 4: Zero-Default Policy. 
        Hard-Halts if JSON data does not match the physical schema definition.
        """
        schema_path = Path(SystemPaths.SCHEMA_DIR) / schema_filename
        try:
            with open(schema_path, 'r', encoding="utf-8") as s:
                schema = json.load(s)
            validate(instance=data, schema=schema)
        except Exception as e:
            logger.critical(f"❌ SCHEMA BREACH: {schema_filename} validation failed.")
            raise RuntimeError(f"CRITICAL: {schema_filename} is corrupt or invalid. {e}")

    @staticmethod
    def mount(config_path: str, data_path: str, ledger_path: str) -> OrchestrationState:
        """
        Mounting Protocol with Auto-Wake Logic.
        Standardized via SystemPaths (Rule 4).
        """
        config_file = Path(config_path)
        dormant_flag = Path(SystemPaths.CONFIG_DIR) / SystemPaths.DORMANT_FLAG

        if dormant_flag.exists() and config_file.exists():
            # Rule 1: Efficiency. New config timestamp overrides hibernation.
            if config_file.stat().st_mtime >= dormant_flag.stat().st_mtime:
                logger.info("🌅 New Configuration detected. Resetting to STATUS: ACTIVE.")
                try:
                    dormant_flag.write_text("STATUS: ACTIVE", encoding="utf-8")
                except OSError as e:
                    logger.error(f"Failed to reset dormancy flag: {e}")
        
        logger.info(f"🛰️ Mounting Engine Foundation: {config_path}")
        return OrchestrationState(config_path, data_path, ledger_path)

    @staticmethod
    def hydrate(state: OrchestrationState) -> dict:
        """
        Fetches remote manifest, validates schema, and returns the synchronized ledger.
        Ensures Memory-Disk parity to prevent stale status overrides.
        """
        try:
            # 1. Validate Local Entry Point
            active_disk_path = Path(SystemPaths.CONFIG_DIR) / SystemPaths.ACTIVE_DISK
            active_disk_data = json.loads(active_disk_path.read_text(encoding="utf-8"))
            Bootloader._validate_integrity(active_disk_data, SystemPaths.ACTIVE_DISK_SCHEMA)

            # 2. Fetch and Validate Remote Manifest
            logger.info(f"🌐 Fetching Remote Manifest: {state.manifest_url}")
            response = requests.get(state.manifest_url, timeout=15)
            response.raise_for_status()
            remote_manifest = response.json()
            Bootloader._validate_integrity(remote_manifest, SystemPaths.MANIFEST_SCHEMA)

            # 3. Forensic Integrity Check (Rule 4 Compliance)
            ledger_path = Path(state.ledger_path)
            target_pid = remote_manifest["project_id"]
            target_mid = remote_manifest["manifest_id"]

            ledger_content = {}
            should_reset = False
            
            if ledger_path.exists():
                try:
                    ledger_content = json.loads(ledger_path.read_text(encoding="utf-8"))
                    meta = ledger_content["metadata"]
                    # Pivot Check: If Project or Manifest changed, we must wipe and seed.
                    if meta["project_id"] != target_pid or meta["manifest_id"] != target_mid:
                        should_reset = True
                except (json.JSONDecodeError, KeyError):
                    should_reset = True
            else:
                should_reset = True

            # 4. Ledger Seeding Logic (Phase C Pivot Hardening)
            if should_reset:
                logger.warning(f"⚠️ Project Shift/Fresh Start: Seeding Ledger for {target_pid}")
                
                # Rule 4: No .get() defaults. Missing keys will trigger KeyError here.
                fresh_steps = {}
                for step in remote_manifest["pipeline_steps"]:
                    fresh_steps[step["name"]] = {
                        "status": OrchestrationStatus.WAITING.value,
                        "last_triggered": None,
                        "timeout_hours": step["timeout_hours"],
                        "target_repo": step["target_repo"]
                    }

                ledger_content = {
                    "metadata": {
                        "project_id": target_pid,
                        "manifest_id": target_mid
                    },
                    "steps": fresh_steps
                }
                
                # Rule 1: Clean Room Sync - Atomic Disk Persistence
                ledger_path.parent.mkdir(parents=True, exist_ok=True)
                ledger_path.write_text(json.dumps(ledger_content, indent=2), encoding="utf-8")
                logger.info("🧹 Ledger seeded and synchronized.")

            # Hydrate State Engine attributes
            state.hydrate_manifest(remote_manifest)
            logger.info(f"✅ Boot Sequence Complete: [{state.project_id}] Hydrated.")
            
            return ledger_content
            
        except Exception as e:
            logger.critical(f"Hydration Failed: {e}")
            raise RuntimeError(f"❌ CRITICAL: Hydration failure. {e}")