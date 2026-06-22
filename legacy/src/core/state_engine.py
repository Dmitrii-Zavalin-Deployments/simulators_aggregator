# src/core/state_engine.py

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from jsonschema import validate

# Internal Core Imports
from src.core.constants import OrchestrationStatus, SystemPaths

logger = logging.getLogger("Engine.State")

class OrchestrationState:
    """
    Forensic Artifact Registry.
    Implements the 'Round-and-Round' Transition Matrix for Nomadic Automation.
    Phase C Compliance: Rule 0 (__slots__), Rule 4 (Zero-Default), and Schema Sovereignty.
    """
    
    # Rule 0: Memory Optimization
    __slots__ = ['project_id', 'manifest_url', 'data_path', 'manifest_data', 'schema_path', 'ledger_path']

    def __init__(self, config_path: str, data_root: str, ledger_path: str):
        """
        Deterministic Initialization.
        Requires explicit ledger_path to ensure Atomic Persistence.
        """
        self.data_path = Path(data_root)
        self.ledger_path = Path(ledger_path)
        
        # Rule 4: Explicit pathing to the Schema Directory
        self.schema_path = Path(SystemPaths.SCHEMA_DIR) / SystemPaths.MANIFEST_SCHEMA
        
        if not self.data_path.exists():
            self.data_path.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_path, 'r', encoding="utf-8") as f:
                config = json.load(f)
                self.project_id = config['project_id']
                self.manifest_url = config['manifest_url']
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
            raise RuntimeError(f"❌ CRITICAL: Mounting Failed. Configuration Breach: {e}")
        
        self.manifest_data = None

    def hydrate_manifest(self, manifest_json: dict):
        """Enforces Schema Sovereignty before allowing hydration."""
        
        # Identity Handshake with Hard-Halt Signature
        if manifest_json.get("project_id") != self.project_id:
            raise RuntimeError(f"❌ CRITICAL: Hard-Halt - Identity Mismatch: Manifest {manifest_json.get('project_id')} does not match Disk {self.project_id}")
        
        try:
            with open(self.schema_path, 'r', encoding="utf-8") as s:
                schema = json.load(s)
            validate(instance=manifest_json, schema=schema)
            
            self.manifest_data = manifest_json
            logger.info(f"💿 Registry Hydrated & Validated: [{manifest_json['manifest_id']}]")
        except Exception as e:
            raise RuntimeError(f"❌ CRITICAL: Hard-Halt. Manifest is corrupt or Schema missing. {e}")

    def _update_status(self, step_name: str, entry: dict, new_status: OrchestrationStatus, reason: str = ""):
        """
        Internal Transition Reporter.
        Ensures every state change is logged for Forensic Auditing.
        """
        # Rule 4 Compliance: Direct access. If status is missing, we WANT a KeyError.
        old_status = entry["status"]
        if old_status != new_status.value:
            entry["status"] = new_status.value
            msg = f"🔄 State Mutation [{step_name}]: {old_status} -> {new_status.value}"
            if reason:
                msg += f" | {reason}"
            logger.info(msg)

    def _is_job_stale(self, job_name: str, ledger: dict) -> bool:
        """Helper: Checks if a job's time-lock has expired."""
        job_data = ledger[job_name]
        last_trigger_str = job_data["last_triggered"]
        
        if last_trigger_str is None:
            return False

        try:
            timeout_h = job_data["timeout_hours"]
            last_trigger = datetime.fromisoformat(last_trigger_str)
            return datetime.now(timezone.utc) > (last_trigger + timedelta(hours=timeout_h))
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"⚠️ Timing Metadata Corruption for {job_name}: {e}")
            return True

    def save_ledger(self, orchestration_ledger_steps: dict):
        """
        Rule 4 Compliance: Atomic Write to Disk.
        Wraps steps in the required root structure to prevent corruption errors.
        """
        # Reconstruct the full object so LedgerManager is happy
        full_ledger = {
            "metadata": {
                "project_id": self.project_id,
                "manifest_id": self.manifest_data["manifest_id"] if self.manifest_data else "unknown"
            },
            "steps": orchestration_ledger_steps
        }

        try:
            with open(self.ledger_path, 'w', encoding="utf-8") as f:
                json.dump(full_ledger, f, indent=2)
            logger.info(f"💾 Ledger Persisted: {self.ledger_path.name}")
        except Exception as e:
            logger.error(f"❌ Persistence Error: Failed to write ledger. {e}")

    def reconcile_and_heal(self, orchestration_ledger: dict):
        """
        The Core Logic Loop: Reconciles the Ledger against Physical Reality.
        Triggers a disk save if any mutations occur.
        """
        if not self.manifest_data:
            raise RuntimeError("❌ CRITICAL: Scan attempted without Manifest Hydration.")

        for step in self.manifest_data["pipeline_steps"]:
            name = step["name"]
            entry = orchestration_ledger[name]
            current_status = entry["status"]
            
            # PHYSICAL TRUTH CHECK
            requires = step["requires"]
            produces = step["produces"]
            inputs_exist = all((self.data_path / f).exists() for f in requires)
            outputs_exist = all((self.data_path / f).exists() for f in produces)

            # --- TRANSITION MATRIX ---

            # 1. Artifact Presence = COMPLETED
            if outputs_exist:
                self._update_status(name, entry, OrchestrationStatus.COMPLETED, "Artifact detected.")

            # 2. Input Saturation = PENDING
            elif current_status == OrchestrationStatus.WAITING.value and inputs_exist:
                self._update_status(name, entry, OrchestrationStatus.PENDING, "Inputs detected.")

            # 3. Input Loss = Revert to WAITING
            elif current_status == OrchestrationStatus.PENDING.value and not inputs_exist:
                self._update_status(name, entry, OrchestrationStatus.WAITING, "Input artifacts missing.")

            # 4. Temporal Monitoring (IN_PROGRESS)
            elif current_status == OrchestrationStatus.IN_PROGRESS.value:
                if self._is_job_stale(name, orchestration_ledger):
                    self._update_status(name, entry, OrchestrationStatus.FAILED, "Execution Timeout.")
                else:
                    logger.info(f"⏳ {name}: In-flight (within timeout window).")

            # 5. Artifact Drift (COMPLETED but file missing)
            elif current_status == OrchestrationStatus.COMPLETED.value and not outputs_exist:
                self._update_status(name, entry, OrchestrationStatus.WAITING, "Artifact drift detected.")

            # 6. FAILED RECOVERY
            elif current_status == OrchestrationStatus.FAILED.value:
                if inputs_exist:
                    self._update_status(name, entry, OrchestrationStatus.PENDING, "Retrying failed step.")
                else:
                    self._update_status(name, entry, OrchestrationStatus.WAITING, "Resetting to Waiting.")

        # --- PERSISTENCE GATE ---
        self.save_ledger(orchestration_ledger)
        return orchestration_ledger

    def get_ready_steps(self, orchestration_ledger: dict):
        """Returns steps currently in PENDING status for the main_engine to trigger."""
        ready_steps = []
        for step in self.manifest_data["pipeline_steps"]:
            name = step["name"]
            status = orchestration_ledger[name]["status"]
            if status == OrchestrationStatus.PENDING.value:
                ready_steps.append(step)
        
        return ready_steps if ready_steps else None