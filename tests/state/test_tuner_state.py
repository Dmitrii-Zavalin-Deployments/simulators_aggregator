import json
import pytest
from src.state.tuner_state import TunerState

# ==============================================================================
# Helper Data
# ==============================================================================

# We define a canonical state object representing a healthy operational baseline.
# This payload is utilized across test cases to ensure consistent validation.
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

# To maintain architectural stability, the TunerState class enforces a strict 
# zero-default policy. We validate that the system rejects any attempt to 
# instantiate an object with incomplete or malformed metadata.

def test_constructor_validation():
    # We iterate through required parameters to ensure the system enforces 
    # explicit configuration (none may be null).
    params = ["pipeline_id", "steps", "task_details", "successful_runs_archive", "failed_runs_archive"]
    
    for param in params:
        test_args = VALID_STATE_DATA.copy()
        test_args[param] = None
        
        with pytest.raises(ValueError, match=f"Missing structural parameter: {param}"):
            TunerState(**test_args)

def test_constructor_steps_deep_validation():
    # The 'steps' attribute is a critical configuration map. We validate:
    # 1. Type safety of the top-level container.
    # 2. Type safety of the individual step configurations.
    # 3. Schema completeness (required fields must be present).
    # 4. Content validity (fields cannot be empty strings).
    test_args = VALID_STATE_DATA.copy()
    
    # Check type rejection for non-mapping structures.
    test_args["steps"] = ["not", "a", "dictionary"]
    with pytest.raises(TypeError, match="must be a dictionary mapping"):
        TunerState(**test_args)
        
    # Check type rejection for malformed step configurations.
    test_args["steps"] = {"1": "invalid_string_config"}
    with pytest.raises(TypeError, match="must be a dictionary configuration"):
        TunerState(**test_args)

    # Check schema compliance (missing required fields).
    test_args["steps"] = {"1": {"input_file_name": "a.json"}} 
    with pytest.raises(ValueError, match="violates validation schema. Missing required fields"):
        TunerState(**test_args)

    # Check field integrity (reject empty values).
    test_args["steps"] = {
        "1": {
            "input_file_name": "a.json",
            "output_file_name": "", 
            "input_output_folder": "out_dir"
        }
    }
    with pytest.raises(ValueError, match="cannot be empty or null"):
        TunerState(**test_args)

# ==============================================================================
# 2. Dehydration & Hydration Validation
# ==============================================================================

# State portability is essential for distributed pipelines. The system must be 
# capable of deconstructing its state into a serializable format (dictionary) 
# and reconstructing itself from that format, provided the schema remains intact.

def test_to_dict_serialization():
    # Verify that the dehydration process preserves exact data mapping.
    # The system must account for all designated slots during serialization.
    state = TunerState(**VALID_STATE_DATA)
    state_dict = state.to_dict()
    
    assert state_dict["pipeline_id"] == "test_pipe"
    assert state_dict["successful_runs_archive"] == "out"
    assert state_dict["failed_runs_archive"] == "err"
    
    for slot in TunerState.__slots__:
        assert slot in state_dict

def test_from_dict_validation():
    # The hydration process acts as a security gate. If the input dictionary 
    # lacks required keys, the system must trigger a critical failure 
    # rather than initializing an incomplete state.
    corrupted_data = VALID_STATE_DATA.copy()
    del corrupted_data["pipeline_id"]
    
    with pytest.raises(KeyError, match="Critical State Corruption"):
        TunerState.from_dict(corrupted_data)

# ==============================================================================
# 3. Disk Persistence Verification
# ==============================================================================

# Persistent state allows for recovery and auditing. We verify the atomic 
# interaction between the memory object and the filesystem, ensuring no data 
# loss occurs during serialization or deserialization.

def test_save_to_disk(tmp_path):
    # Verify that the system atomically serializes internal slots to disk.
    file_path = tmp_path / "saved_state.json"
    state = TunerState(**VALID_STATE_DATA)
    
    state.save_to_disk(str(file_path))
    
    assert file_path.exists()
    with open(file_path, "r") as f:
        raw_json_data = json.load(f)
        
    assert raw_json_data["pipeline_id"] == "test_pipe"
    assert raw_json_data["steps"]["1"]["output_file_name"] == "b.json"

def test_load_from_disk(tmp_path):
    # Verify the inverse operation: Reconstructing a fully typed object from 
    # a persisted JSON file on the disk.
    file_path = tmp_path / "state.json"
    with open(file_path, 'w') as f:
        json.dump(VALID_STATE_DATA, f)
        
    state = TunerState.load_from_disk(str(file_path))
    
    assert state.pipeline_id == "test_pipe"
    assert state.steps["1"]["input_file_name"] == "a.json"
    assert state.steps["1"]["output_file_name"] == "b.json"

# ==============================================================================
# 4. Schema Compliance
# ==============================================================================

# The 'to_saap_deliverable' method transforms internal system state into the 
# formalized output structure required for external API and logging consumers.

def test_to_saap_deliverable():
    # Verify the conversion from flat internal state to the nested, 
    # deliverable-compliant schema.
    state = TunerState(**VALID_STATE_DATA)
    
    deliverable = state.to_saap_deliverable()
    
    # Assert structural integrity and data mapping within the deliverable format.
    assert "task" in deliverable
    assert "deliverables" in deliverable
    assert deliverable["task"]["pipeline_id"] == "test_pipe"
    assert deliverable["task"]["steps"]["1"]["input_output_folder"] == "out_dir"
    assert deliverable["deliverables"]["successful_runs_archive"] == "out"