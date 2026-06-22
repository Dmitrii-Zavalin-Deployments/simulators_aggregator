# tests/architecture/test_performance_law.py

import pytest
from src.core.state_engine import OrchestrationState
from src.io.download_from_dropbox import CloudIngestor
from src.io.dropbox_utils import TokenManager
from src.core.update_ledger import LedgerManager

@pytest.mark.parametrize("target_class", [
    OrchestrationState, 
    CloudIngestor, 
    TokenManager,
    LedgerManager
])
def test_mandatory_slots_compliance(target_class):
    """
    CONSTITUTION CHECK: Phase C (0) - The Law of Performance.
    Verifies that core classes use __slots__ to eliminate memory overhead.
    """
    # Classes with __slots__ do NOT have a __dict__ attribute.
    # This is the primary verification for Rule 0.
    assert hasattr(target_class, "__slots__"), (
        f"❌ ARCHITECTURE BREACH: {target_class.__name__} is missing __slots__. "
        "Memory efficiency mandate failed."
    )
    
    # Instantiate a dummy or check the class attribute directly
    assert isinstance(target_class.__slots__, (list, tuple)), (
        f"❌ {target_class.__name__}.__slots__ must be a list or tuple."
    )
    
    print(f"✅ Rule 0 Verified: {target_class.__name__} compliant with __slots__ architecture.")

def test_deterministic_init_signature():
    """
    CONSTITUTION CHECK: Phase C (0) - Deterministic Initialization.
    Verifies that OrchestrationState requires explicit path injection.
    """
    import inspect
    sig = inspect.signature(OrchestrationState.__init__)
    params = sig.parameters
    
    # Must have explicit config, data, and ledger paths as defined in Phase C (0) 
    required_params = ['config_path', 'data_root', 'ledger_path']
    for param in required_params:
        assert param in params, f"❌ OrchestrationState.__init__ missing mandatory path injection: {param}"
        
    print("✅ Rule 5 Verified: OrchestrationState enforces Deterministic Path Initialization.")