# tests/architecture/test_vulture_clean.py

import subprocess
import pytest

def test_vulture_dead_code_audit():
    """
    CONSTITUTION CHECK: Phase C (6) - Forensic Deletion Rule.
    Uses 'vulture' to scan for unused code that violates the Zero-Debt Mandate.
    """
    # 1. Check if vulture is installed
    try:
        pass
    except ImportError:
        pytest.skip("Vulture not installed. Run 'pip install vulture' to enforce Rule 6.")

    # 2. Execute Vulture scan on the src directory
    # We set min_confidence to 80 to avoid false positives on dynamically called methods
    result = subprocess.run(
        ["vulture", "src/", "--min-confidence", "80"],
        capture_output=True,
        text=True
    )

    # RULE: Any output from vulture indicates potential dead code (Debt).
    if result.stdout:
        print("\n--- 💀 DEAD CODE DETECTED ---")
        print(result.stdout)
        pytest.fail("❌ ARCHITECTURAL VIOLATION: Dead code found in src/. Follow the Forensic Deletion Rule.")

    print("✅ Rule 6 Verified: Codebase is lean and debt-free.")

def test_api_minimization_check():
    """
    CONSTITUTION CHECK: Phase C (6) - API Minimalism.
    Verifies that public methods in core classes are accounted for in the orchestration cycle.
    """
    from src.core.state_engine import OrchestrationState
    import inspect

    # List of "Sovereign" methods allowed to exist in OrchestrationState
    allowed_methods = {
        '__init__', 'hydrate_manifest', 'save_ledger', 
        'reconcile_and_heal', 'get_ready_steps', '_update_status', '_is_job_stale'
    }

    current_methods = {name for name, _ in inspect.getmembers(OrchestrationState, predicate=inspect.isfunction)}
    
    # Check for "Zombie" methods (extra logic not defined in the architecture)
    zombies = current_methods - allowed_methods
    assert not zombies, f"❌ DEBT DETECTED: OrchestrationState has unauthorized methods: {zombies}"
    
    print("✅ Rule 6 Verified: OrchestrationState API is minimized.")