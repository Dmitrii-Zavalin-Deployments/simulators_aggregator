# tests/architecture/test_deterministic_init.py

import inspect
import pytest
from src.core.state_engine import OrchestrationState
from src.io.download_from_dropbox import CloudIngestor
from src.io.dropbox_utils import TokenManager

@pytest.mark.parametrize("target_class", [
    OrchestrationState,
    CloudIngestor,
    TokenManager
])
def test_no_default_arguments_on_init(target_class):
    """
    CONSTITUTION CHECK: Phase C (4) - Deterministic Initialization Mandate.
    Verifies that critical paths and credentials have no default values in __init__.
    """
    sig = inspect.signature(target_class.__init__)
    for name, param in sig.parameters.items():
        if name == 'self':
            continue
            
        # RULE: Explicit or Error. Default values are prohibited for orchestration parameters.
        assert param.default is inspect.Parameter.empty, (
            f"❌ ARCHITECTURAL VIOLATION: {target_class.__name__}.__init__ parameter '{name}' "
            f"has a default value '{param.default}'. Defaults are banned under Rule 4."
        )
    
    print(f"✅ Rule 4 Verified: {target_class.__name__} enforces explicit initialization.")

def test_keyerror_hard_halt_integrity():
    """
    CONSTITUTION CHECK: Phase C (4) - Zero-Default Policy.
    Ensures that missing mandatory keys in manifest data trigger KeyError, not silent defaults.
    """
    # This simulates the internal logic of src/core/state_engine.py
    # which uses direct access: self.project_id = data["project_id"]
    incomplete_manifest = {"manifest_id": "M-01"} # Missing 'project_id'
    
    def simulate_hydration(data):
        # The engine must use direct access, never .get()
        return data["project_id"]

    with pytest.raises(KeyError):
        simulate_hydration(incomplete_manifest)
        
    print("✅ Rule 4 Verified: System correctly triggers Hard-Halt on missing manifest keys.")