import json
import pytest
from src.state.tuner_state import TunerState

# ==============================================================================
# Helper Data
# ==============================================================================

# We define valid, minimal state data to be reused across tests.
VALID_STATE_DATA = {
    "pipeline_id": "test_pipe",
    "steps": {
        "1": {
            "input_file_name": "a.json",
            "output_file_name": "b.json",
            "input_output_folder": "out_dir"
        }
    },
    "task_details": [{"step": 1}],
    "successful_runs_archive": "out",
    "failed_runs_archive": "err"
}

# ==============================================================================
# 1. Constructor Validation (Covers strict Zero-Default Policy & Types)
# ==============================================================================

def test_constructor_validation():
    # We iterate through each required parameter, ensuring None raises ValueError.
    params = ["pipeline_id", "steps", "task_details", "successful_runs_archive", "failed_runs_archive"]
    
    for param in params:
        test_args = VALID_STATE_DATA.copy()
        test_args[param] = None
        
        # We assert that initializing with None results in a ValueError for that specific parameter.
        with pytest.raises(ValueError, match=f"Missing structural parameter: {param}"):
            TunerState(**test_args)

def test_constructor_steps_deep_validation():
    test_args = VALID_STATE_DATA.copy()
    
    # 1. Check type rejection if steps is not a dictionary mapping
    test_args["steps"] = ["not", "a", "dictionary"]
    with pytest.raises(TypeError, match="must be a dictionary mapping"):
        TunerState(**test_args)
        
    # 2. Check type rejection if a specific step item is not a dictionary configuration
    test_args["steps"] = {"1": "invalid_string_config"}
    with pytest.raises(TypeError, match="must be a dictionary configuration"):
        TunerState(**test_args)

    # 3. Check structural validation when required keys are missing inside a step configuration
    test_args["steps"] = {"1": {"input_file_name": "a.json"}}  # missing output_file_name & input_output_folder
    with pytest.raises(ValueError, match="violates validation schema. Missing required fields"):
        TunerState(**test_args)

    # 4. Check validation rejection if a field contains an empty string or null value
    test_args["steps"] = {
        "1": {
            "input_file_name": "a.json",
            "output_file_name": "",  # Empty string violation
            "input_output_folder": "out_dir"
        }
    }
    with pytest.raises(ValueError, match="cannot be empty or null"):
        TunerState(**test_args)

# ==============================================================================
# 2. Dehydration & Hydration Validation
# ==============================================================================

def test_to_dict_serialization():
    """Triggers Line 73: Verifies explicit serialization matching exact slots structural layout."""
    state = TunerState(**VALID_STATE_DATA)
    state_dict = state.to_dict()
    
    assert state_dict["pipeline_id"] == "test_pipe"
    assert state_dict["successful_runs_archive"] == "out"
    assert state_dict["failed_runs_archive"] == "err"
    
    # Ensure every designated slot attribute is accurately parsed into the output map keys
    for slot in TunerState.__slots__:
        assert slot in state_dict

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
# 3. Disk Persistence Verification
# ==============================================================================

def test_save_to_disk(tmp_path):
    """Triggers Lines 92-93: Verifies atomic disk writes serialize context parameters correctly."""
    file_path = tmp_path / "saved_state.json"
    state = TunerState(**VALID_STATE_DATA)
    
    # Execution: Serialize instance data down to file target path
    state.save_to_disk(str(file_path))
    
    # Assertion: Confirm target file physically exists and reads back perfectly parsed JSON
    assert file_path.exists()
    with open(file_path, "r") as f:
        raw_json_data = json.load(f)
        
    assert raw_json_data["pipeline_id"] == "test_pipe"
    assert raw_json_data["steps"]["1"]["output_file_name"] == "b.json"

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
    assert state.steps["1"]["input_file_name"] == "a.json"
    assert state.steps["1"]["output_file_name"] == "b.json"

# ==============================================================================
# 4. Schema Compliance
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
    assert deliverable["task"]["steps"]["1"]["input_output_folder"] == "out_dir"
    assert deliverable["deliverables"]["successful_runs_archive"] == "out"