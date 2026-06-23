import os
from src.state.tuner_state import TunerState
from src.pipeline.steps.execution_engine import ExecutionEngineStep
from src.pipeline.steps.deliverable_assembly import DeliverableAssemblyStep

# --- Configuration Paths ---
STATE_FILE_PATH = "tuner_state.json"
DORMANCY_FLAG_PATH = "config/dormant.flag"

def check_dormancy() -> bool:
    """Evaluates the Isolation Mandate."""
    if not os.path.exists(DORMANCY_FLAG_PATH):
        return False # Active by default
    with open(DORMANCY_FLAG_PATH, 'r') as f:
        return "STATUS: DORMANT" in f.read()

def enforce_dormancy():
    """Locks the engine into hibernation."""
    os.makedirs(os.path.dirname(DORMANCY_FLAG_PATH), exist_ok=True)
    with open(DORMANCY_FLAG_PATH, 'w') as f:
        f.write("STATUS: DORMANT\n")

def run_pulse():
    """
    The Master Entrypoint.
    Executes a single hourly pulse of the ACE pipeline.
    """
    # 1. Gatekeeper Verification
    if check_dormancy():
        print("🛑 ENGINE DORMANT: Halting pulse. No active targets.")
        return

    print("🚀 ENGINE ACTIVE: Initiating Hydration...")

    # 2. Strict Hydration
    if not os.path.exists(STATE_FILE_PATH):
        raise FileNotFoundError(f"CRITICAL: {STATE_FILE_PATH} missing. Initial state generation required.")
    
    state = TunerState.load_from_disk(STATE_FILE_PATH)
    
    # 3. Execution Engine (ACE Loop)
    ExecutionEngineStep().execute(state)

    # 4. Exit Gate & Lifecycle Management
    if state.batch_cursor >= len(state.combinations_to_test):
        print("✅ Super-Matrix saturated. Assembling SaaP Deliverables...")
        DeliverableAssemblyStep().execute(state)
        enforce_dormancy()
    
    # 5. Dehydration (Atomic Persistence)
    state.save_to_disk(STATE_FILE_PATH)
    
    # 6. Audit Logging
    print(f"💾 Dehydration complete. Cursor position: [{state.batch_cursor} / {len(state.combinations_to_test)}]")


if __name__ == "__main__":
    # pragma: no cover (Forensic Deletion Rule: Boilerplate ignored by coverage)
    run_pulse()