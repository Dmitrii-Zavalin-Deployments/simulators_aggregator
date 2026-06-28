import json
import pytest
import logging
from unittest.mock import patch
from src.pipeline import matrix_exploder

# ==============================================================================
# 1. Logic Verification: The Recursive Exploder
# ==============================================================================

# The core of the matrix exploder is the `explode_dict` function. It must 
# recursively process dictionaries to compute Cartesian products. 
# We verify that it correctly handles flat values and nested dictionaries.
def test_explode_dict_recursion():
    # Setup a nested structure mimicking a 'boundary_map'
    input_map = {
        "x": [1, 2],
        "params": {"y": [10, 20]}
    }
    
    # Expected result: Cartesian product of x and y
    # (1, 10), (1, 20), (2, 10), (2, 20)
    result = matrix_exploder.explode_dict(input_map)
    
    assert len(result) == 4
    assert {"x": 1, "params": {"y": 10}} in result
    assert {"x": 2, "params": {"y": 20}} in result

# ==============================================================================
# 2. Main Orchestrator: Failure Modes & Logging
# ==============================================================================

# The `main()` function interfaces with the filesystem and CLI. It is crucial 
# that it reports errors via the logger before exiting, ensuring the 
# CI pipeline failure is transparent.

# Scenario: The input configuration file does not exist.
# The system must log an error and raise a SystemExit(1).
def test_main_file_not_found(tmp_path, caplog):
    config_path = tmp_path / "missing.json"
    output_path = tmp_path / "out.json"
    
    with caplog.at_level(logging.ERROR):
        with patch("sys.argv", ["script", "--config-path", str(config_path), "--output-path", str(output_path)]):
            with pytest.raises(SystemExit) as exc:
                matrix_exploder.main()
            assert exc.value.code == 1
    
    assert "❌ Configuration file not found" in caplog.text

# Scenario: The input file contains invalid JSON data.
# The system must catch the decode error and log the issue clearly.
def test_main_invalid_json(tmp_path, caplog):
    config_path = tmp_path / "bad.json"
    config_path.write_text("{ incomplete json")
    output_path = tmp_path / "out.json"
    
    with caplog.at_level(logging.ERROR):
        with patch("sys.argv", ["script", "--config-path", str(config_path), "--output-path", str(output_path)]):
            with pytest.raises(SystemExit) as exc:
                matrix_exploder.main()
            assert exc.value.code == 1
    
    assert "❌ Failed to parse JSON" in caplog.text

# ==============================================================================
# 3. Integration: Success Path
# ==============================================================================

# Finally, we verify the end-to-end success path. When provided with a valid
# configuration, the system must generate the correct number of permutations
# and save them to the requested output file.
def test_main_success_path(tmp_path, caplog):
    # Setup valid configuration
    config_path = tmp_path / "config.json"
    output_path = tmp_path / "result.json"
    
    config_data = {
        "learning_rate": [0.01, 0.001],
        "boundary_map": {"width": [10, 20]}
    }
    config_path.write_text(json.dumps(config_data))
    
    # Run main logic
    with caplog.at_level(logging.INFO):
        with patch("sys.argv", ["script", "--config-path", str(config_path), "--output-path", str(output_path)]):
            matrix_exploder.main()
    
    # Verify success logs
    assert "✅ Success: Generated 4 permutations" in caplog.text
    assert output_path.exists()
    
    # Verify file content
    with open(output_path, "r") as f:
        data = json.load(f)
        assert len(data) == 4
        # Verify the cross-product logic was applied correctly
        assert {"learning_rate": 0.01, "boundary_map": {"width": 10}} in data
        assert {"learning_rate": 0.001, "boundary_map": {"width": 20}} in data

# Covers Line 20: Input to recursive function is not a dictionary
def test_explode_dict_non_dict_input():
    # Passing an integer should just return it wrapped in a list
    assert matrix_exploder.explode_dict(100) == [100]

# Covers Line 30: Inside the dictionary, a value is a scalar (not list/dict)
def test_explode_dict_scalar_value():
    # Input has a scalar '5', which falls into the 'else' block
    input_data = {"key": 5}
    assert matrix_exploder.explode_dict(input_data) == [{"key": 5}]

# Covers Line 68: Root-level key is a scalar (not a list, not 'boundary_map')
def test_main_with_scalar_values(tmp_path):
    config_path = tmp_path / "config.json"
    output_path = tmp_path / "result.json"
    
    # "learning_rate" is a scalar, forcing the code into the 'else' block
    config_data = {"learning_rate": 0.01} 
    config_path.write_text(json.dumps(config_data))
    
    with patch("sys.argv", ["script", "--config-path", str(config_path), "--output-path", str(output_path)]):
        matrix_exploder.main()
        
    with open(output_path, "r") as f:
        data = json.load(f)
        # Should create a list with one dict containing the scalar
        assert data == [{"learning_rate": 0.01}]