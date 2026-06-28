import json
import pytest
import os
from src.state.tuner_state import TunerState

# ==============================================================================
# Helper Data
# ==============================================================================

# We define valid, minimal state data to be reused across tests.
VALID_STATE_DATA = {
    "pipeline_id": "test_pipe",
    "input_data_list": ["a.json"],
    "task_details": [{"step": 1}],
    "successful_runs_archive": "out",
    "failed_runs_archive": "err"
}

# ==============================================================================
# 1. Constructor Validation (Covers lines 33, 35, 37, 39, 41)
# ==============================================================================

# The TunerState enforces a strict Zero-Default Policy.
# If any required parameter is None, the constructor must raise a ValueError.
def test_constructor_validation():
    # We iterate through each required parameter, ensuring None raises ValueError.
    params = ["pipeline_id", "input_data_list", "task_details", "successful_runs_archive", "failed_runs_archive"]
    
    for param in params:
        test_args = VALID_STATE_DATA.copy()
        test_args[param] = None
        
        # We assert that initializing with None results in a ValueError for that specific parameter.
        with pytest.raises(ValueError, match=f"Missing structural parameter: {param}"):
            TunerState(**test_args)

# ==============================================================================
# 2. Dehydration & Hydration Validation (Covers lines 59-63)
# ==============================================================================

# Reconstruction of the state from a dictionary requires the exact internal schema.
# If a key is missing from the dictionary, the system must raise a KeyError 
# to prevent state corruption.
def test_from_dict_validation():
    # We remove a key from the valid state to simulate data corruption.
    corrupted_data = VALID_STATE_DATA.copy()
    del corrupted_data["pipeline_id"]
    
    # We assert that the class refuses to hydrate from incomplete data.
    with pytest.raises(KeyError, match="Critical State Corruption"):
        TunerState.from_dict(corrupted_data)

# ==============================================================================
# 3. Disk Persistence Verification (Covers lines 79-81)
# ==============================================================================

# The state must be serializable and deserializable from disk.
# We verify the load_from_disk method correctly reads and parses the JSON.
def test_load_from_disk(tmp_path):
    # Setup: Write a valid JSON file to a temporary location.
    file_path = tmp_path / "state.json"
    with open(file_path, 'w') as f:
        json.dump(VALID_STATE_DATA, f)
        
    # Execution: Load the object back from disk.
    state = TunerState.load_from_disk(str(file_path))
    
    # Assertion: Verify the properties are correctly assigned.
    assert state.pipeline_id == "test_pipe"
    assert state.input_data_list == ["a.json"]

# ==============================================================================
# 4. Schema Compliance (Covers line 90)
# ==============================================================================

# The `to_saap_deliverable` method must transform the internal flat state
# into the nested dictionary structure required by the Tuner Output Schema.
def test_to_saap_deliverable():
    state = TunerState(**VALID_STATE_DATA)
    
    # Execution: Transform to output schema.
    deliverable = state.to_saap_deliverable()
    
    # Verification: Ensure the top-level keys ('task', 'deliverables') exist 
    # and contain the expected nested structure.
    assert "task" in deliverable
    assert "deliverables" in deliverable
    assert deliverable["task"]["pipeline_id"] == "test_pipe"
    assert deliverable["deliverables"]["successful_runs_archive"] == "out"