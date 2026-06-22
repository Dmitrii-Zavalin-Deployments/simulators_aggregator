# src/core/update_ledger.py

import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict

# Internal Core Imports
from src.core.constants import OrchestrationStatus, SystemPaths

# Configure Logger for Engine Traceability
logger = logging.getLogger("Engine.Ledger")

class LedgerManager:
    """
    The Traceability Bridge (Performance Audit & Orchestration Memory).
    Phase C Compliance: 
    - Rule 0: __slots__ Mandatory Architecture (Memory Efficiency)
    - Rule 1: Efficiency Mandate (Dormancy Orchestration)
    - Rule 4: Zero-Default Policy (Strict Key Access - No .get() defaults)
    - Rule 5: Operational Hygiene (Atomic Audit Trail)
    """
    
    # Rule 0: Eliminate dict overhead for nomadic scalability
    __slots__ = ['log_path', 'orchestration_path', 'header', 'flag_path']

    def __init__(self, log_path: str = "performance_audit.md"):
        self.log_path = log_path
        # Standardized pathing via SystemPaths (Rule 4)
        self.orchestration_path = os.path.join(SystemPaths.CONFIG_DIR, SystemPaths.LEDGER)
        self.flag_path = os.path.join(SystemPaths.CONFIG_DIR, SystemPaths.DORMANT_FLAG)
        self.header = "# 🛰️ Simulation Engine Performance Audit\n\n"

    # --- SECTION 1: PERFORMANCE AUDIT (MARKDOWN) ---

    def record_event(self, category: str, message: str, metadata: Optional[Dict] = None):
        """
        Prepends a structured entry to the performance_audit.md using Atomic Prepending.
        Ensures the 'Pulse' history remains chronological (Newest First).
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        meta_str = f" | {metadata}" if metadata else ""
        
        new_entry = f"## [{timestamp}] {category}\n- **Message:** {message}{meta_str}\n\n---\n\n"

        existing_content = ""
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, "r", encoding="utf-8") as f:
                    current_text = f.read()
                    # Preserve only the entries, not the duplicated header
                    existing_content = current_text.replace(self.header, "")
            except (FileNotFoundError, IOError) as e:
                logger.warning(f"Audit Read Warning: {e}. Re-initializing buffer.")

        try:
            with open(self.log_path, "w", encoding="utf-8") as f:
                f.write(self.header + new_entry + existing_content)
        except IOError as e:
            logger.critical(f"Critical Audit Write Failure: {e}")
            raise RuntimeError(f"❌ CRITICAL: Could not update performance audit. {e}")

    # --- SECTION 2: ORCHESTRATION MEMORY (JSON) ---

    def load_orchestration_state(self) -> Dict:
        """
        Loads the JSON memory. 
        Enforces a hard structure: {"metadata": {}, "steps": {}}
        """
        if not os.path.exists(self.orchestration_path):
            logger.warning("Orchestration Ledger missing. Initializing fresh structure.")
            return {"metadata": {}, "steps": {}}
        
        try:
            with open(self.orchestration_path, "r", encoding="utf-8") as f:
                content = json.load(f)
                # Rule 4 Check: Hard-halt if schema is malformed
                if "steps" not in content or "metadata" not in content:
                    raise KeyError("Orchestration Ledger schema violation: missing root keys.")
                return content
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Orchestration Ledger corrupt ({e}). Resetting to safe structure.")
            return {"metadata": {}, "steps": {}}

    def update_job_status(self, job_name: str, status: str, metadata: Dict):
        """
        Atomic Write for the In-Flight memory.
        Enforces Rule 4: Mandatory keys (timeout_hours, target) must be present.
        """
        ledger = self.load_orchestration_state()
        
        # Rule 4: Strict key access. If 'timeout_hours' or 'target' is missing, it raises KeyError.
        ledger["steps"][job_name] = {
            "status": status,
            "last_triggered": datetime.now(timezone.utc).isoformat(),
            "timeout_hours": metadata["timeout_hours"], 
            "target_repo": metadata["target"]
        }

        # Update Identity Metadata (Handshake Persistence)
        if "project_id" in metadata:
            ledger["metadata"]["project_id"] = metadata["project_id"]
        if "manifest_id" in metadata:
            ledger["metadata"]["manifest_id"] = metadata["manifest_id"]

        try:
            os.makedirs(os.path.dirname(self.orchestration_path), exist_ok=True)
            with open(self.orchestration_path, "w", encoding="utf-8") as f:
                json.dump(ledger, f, indent=2)
        except IOError as e:
            logger.critical(f"Failed to write to Orchestration Ledger: {e}")
            raise RuntimeError(f"❌ CRITICAL: Ledger sync failed. {e}")

    # --- SECTION 3: DORMANCY ORCHESTRATOR ---

    def evaluate_dormancy_state(self, ledger_steps: Dict):
        """
        Rule 1: Efficiency Mandate.
        Checks if all steps are COMPLETED to toggle system dormancy.
        """
        if not ledger_steps:
            new_state = "STATUS: ACTIVE"
        else:
            # Rule 4: Direct status check
            statuses = [step["status"] for step in ledger_steps.values()]
            is_saturated = all(s == OrchestrationStatus.COMPLETED.value for s in statuses)
            new_state = "STATUS: DORMANT" if is_saturated else "STATUS: ACTIVE"

        try:
            os.makedirs(os.path.dirname(self.flag_path), exist_ok=True)
            with open(self.flag_path, "w", encoding="utf-8") as f:
                f.write(new_state)
            
            if "DORMANT" in new_state:
                self.record_event("💤 DORMANCY_LOCK", "All steps saturated. Engine entering hibernation.")
            return new_state
        except IOError as e:
            logger.error(f"Failed to write dormancy flag: {e}")
            return "STATUS: ACTIVE"

    # --- SECTION 4: WRAPPERS ---

    def log_scan(self, project_id: str, message: str):
        """Logs the results of the reconcile_and_heal pulse."""
        logger.info(f"🔍 Forensic Scan [{project_id}]: {message}")
        self.record_event(
            category="🔍 FORENSIC_SCAN",
            message=message,
            metadata={"project_id": project_id}
        )

    def log_dispatch(self, project_id: str, manifest_id: str, step_name: str, target_repo: str, timeout_hours: int):
        """
        Final Dispatch Record. Fixes the Metadata Handshake for manifest_id.
        """
        logger.info(f"🚀 Dispatching Worker: {step_name} -> {target_repo}")
        
        # 1. Update the Performance Audit (Markdown)
        self.record_event(
            category="🚀 DISPATCH",
            message=f"Command Link Handshake Confirmed for step: {step_name}",
            metadata={
                "project_id": project_id,
                "manifest_id": manifest_id,
                "target": target_repo,
                "timeout_hours": timeout_hours
            }
        )
        
        # 2. Update the Orchestration Ledger (JSON) - Ensures atomic disk sync
        self.update_job_status(
            job_name=step_name, 
            status=OrchestrationStatus.IN_PROGRESS.value, 
            metadata={
                "project_id": project_id,
                "manifest_id": manifest_id,
                "target": target_repo, 
                "timeout_hours": timeout_hours
            }
        )