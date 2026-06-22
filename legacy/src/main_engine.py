# src/main_engine.py

import sys
import logging
from pathlib import Path

# Internal Core Imports
from src.core.constants import OrchestrationStatus, SystemPaths
from src.core.bootloader import Bootloader
from src.api.github_trigger import Dispatcher
from src.core.update_ledger import LedgerManager

# Rule 5: Standardized Logging Format for Audit Trail
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("Engine.Main")

def run_engine():
    """
    The Sovereign Logic Gate.
    Phase C Compliance:
    - Rule 1: Efficiency Mandate (Dormancy Toggle)
    - Rule 4: Zero-Default Policy (Hard-Halt on Missing Keys)
    - Memory-Disk Sync: Bootloader return overrides stale disk reads.
    """
    CONFIG_PATH = Path(SystemPaths.CONFIG_DIR) / SystemPaths.ACTIVE_DISK
    # Rule 4: Explicit Ledger Path for Atomic Persistence
    LEDGER_PATH = Path(SystemPaths.CONFIG_DIR) / SystemPaths.LEDGER
    DATA_PATH = Path(SystemPaths.DATA_DIR)
    
    # 1. Initialize Ledger Manager (For performance_audit.md and flag toggling)
    ledger_manager = LedgerManager(log_path="performance_audit.md")

    # 2. Boot & Auto-Wake (The Ignition Phase)
    try:
        # Rule 4: Mount must find the physical active_disk.json or Hard-Halt.
        # We now pass LEDGER_PATH to ensure OrchestrationState can save its own mutations.
        state = Bootloader.mount(str(CONFIG_PATH), str(DATA_PATH), str(LEDGER_PATH))
        
        # CRITICAL FIX: Capture the synchronized ledger from Bootloader.
        # This prevents the engine from using stale data from a previous project run.
        orchestration_data = Bootloader.hydrate(state)
        
        ledger_manager.record_event("📥 HYDRATION", f"State synchronized for Project: {state.project_id}")
    except Exception as e:
        logger.critical(f"Boot Failure: {e}")
        sys.exit(1)

    # 3. Reconcile (The ROUND-AND-ROUND Phase)
    # Rule 4: We use the 'steps' from our fresh orchestration_data.
    # reconcile_and_heal verifies physical truth and AUTOMATICALLY persists to disk.
    updated_steps = state.reconcile_and_heal(orchestration_data["steps"])
    
    # 4. Evaluate Dormancy (The Efficiency Gate)
    # Rule 1: If all steps are COMPLETED, toggle STATUS: DORMANT to save compute.
    dormancy_status = ledger_manager.evaluate_dormancy_state(updated_steps)
    
    if "DORMANT" in dormancy_status:
        logger.info("✅ MISSION COMPLETE: All artifacts present. System entering hibernation.")
        return

    # 5. Identify Ready Tasks (The READY Phase)
    target_steps = state.get_ready_steps(updated_steps)

    if not target_steps:
        # Check if workers are still in-flight (IN_PROGRESS)
        in_flight = any(s["status"] == OrchestrationStatus.IN_PROGRESS.value 
                        for s in updated_steps.values())
        
        if in_flight:
            logger.info("⏳ PULSE IDLE: Workers are currently in-flight. Awaiting arrival.")
        else:
            logger.info("❓ NO READY STEPS: Dependencies likely blocked or missing.")
        return

    # 6. Dispatch (The TRIGGER phase)
    logger.info(f"🚀 Pulse Detected: {len(target_steps)} tasks ready for activation.")
    dispatcher = Dispatcher()
    
    for step in target_steps:
        try:
            # Rule 4: Strict key access.
            manifest_id = state.manifest_data["manifest_id"]
            
            payload = {
                "project_id": state.project_id,
                "manifest_id": manifest_id,
                "step": step['name'],
                "requires": step['requires'],
                "produces": step['produces']
            }
            
            # Logic Gate: Signal the Remote Worker
            if dispatcher.trigger_worker(step['target_repo'], payload):
                # log_dispatch updates JSON memory status to IN_PROGRESS
                # and performs a final sync of the orchestration_ledger.json.
                ledger_manager.log_dispatch(
                    project_id=state.project_id, 
                    manifest_id=manifest_id, 
                    step_name=step['name'], 
                    target_repo=step['target_repo'],
                    timeout_hours=step['timeout_hours']
                )
            else:
                logger.error(f"❌ DISPATCH FAILED: {step['target_repo']} - Manual check required.")

        except KeyError as e:
            logger.critical(f"Protocol Breach: Missing mandatory manifest key {e}")
            sys.exit(1)

    logger.info("🏁 Cycle Complete: All identified ready-tasks dispatched.")

if __name__ == "__main__": # pragma: no cover
    run_engine()