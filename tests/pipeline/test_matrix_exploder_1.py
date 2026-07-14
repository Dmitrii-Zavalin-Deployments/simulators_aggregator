import json
import pytest
import logging
from unittest.mock import patch
from src.pipeline import matrix_exploder

# ==============================================================================
# 1. Logic Verification: The Recursive Exploder
# ==============================================================================

# The `explode_dict` function is the engine of our configuration processing.
# It must recursively traverse a dictionary and compute the Cartesian product 
# of all lists found within it.

# We test the standard recursive path where both keys and nested structures exist.
# Input structure: {"x": [1, 2], "params": {"y": [10, 20]}}
# Expected outcome: 4 combinations (2x2) correctly maintaining the nested hierarchy.
def test_explode_dict_recursion():
    input_map = {
        "x": [1, 2],
        "params": {"y": [10, 20]}
    }
    
    result = matrix_exploder.explode_dict(input_map)
    
    # Assert we have exactly 2 * 2 = 4 permutations.
    assert len(result) == 4
    # Assert structural integrity for a specific permutation.
    assert {"x": 1, "params": {"y": 10}} in result
    assert {"x": 2, "params": {"y": 20}} in result

# To ensure robustness, we define the behavior when the input is not a dictionary.
# The system must return the input wrapped in a list, treating it as a single unit.
def test_explode_dict_non_dict_input():
    # Input is an integer; the function must return [100].
    val = 100
    assert matrix_exploder.explode_dict(val) == [100]

# We must verify the leaf-node handling. If the value within the dictionary is 
# neither a list nor a dictionary (e.g., a scalar integer), it must be treated 
# as a single-element list to maintain the Cartesian product logic.
def test_explode_dict_scalar_value():
    input_data = {"key": 5}
    # Expected: {"key": 5} wrapped in a list.
    assert matrix_exploder.explode_dict(input_data) == [{"key": 5}]

# ==============================================================================
# 2. Main Orchestrator: Failure Modes & Logging
# ==============================================================================

# The `main()` function manages filesystem I/O and CLI execution. 
# It must handle failures gracefully, ensuring the user is notified via logs
# and the process exits with a non-zero status code.

# Scenario: The input configuration file path is invalid.
# The system must log an error and perform a SystemExit.
def test_main_file_not_found(tmp_path, caplog):
    config_path = tmp_path / "missing.json"
    output_path = tmp_path / "out.json"
    
    with caplog.at_level(logging.ERROR):
        with patch("sys.argv", ["script", "--config-path", str(config_path), "--output-path", str(output_path)]):
            with pytest.raises(SystemExit) as exc:
                matrix_exploder.main()
            # Assert failure code 1
            assert exc.value.code == 1
    
    # Assert error log presence
    assert "❌ Configuration file not found" in caplog.text

# Scenario: The input file is malformed JSON.
# The system must catch the decode error and log it clearly.
def test_main_invalid_json(tmp_path, caplog):
    config_path = tmp_path / "bad.json"
    config_path.write_text("{ incomplete json")
    output_path = tmp_path / "out.json"
    
    with caplog.at_level(logging.ERROR):
        with patch("sys.argv", ["script", "--config-path", str(config_path), "--output-path", str(output_path)]):
            with pytest.raises(SystemExit) as exc:
                matrix_exploder.main()
            # Assert failure code 1
            assert exc.value.code == 1
    
    assert "❌ Failed to parse JSON" in caplog.text

# ==============================================================================
# 3. Integration: Success Path
# ==============================================================================

# We define the happy path where a valid configuration is provided.
# The system must generate the correct permutations and write them to the 
# designated output file.
def test_main_success_path(tmp_path, caplog):
    config_path = tmp_path / "config.json"
    output_path = tmp_path / "result.json"
    
    # Valid setup: Cross-product of lists (2 x 2 = 4 combinations).
    config_data = {
        "learning_rate": [0.01, 0.001],
        "boundary_map": {"width": [10, 20]}
    }
    config_path.write_text(json.dumps(config_data))
    
    with caplog.at_level(logging.INFO):
        with patch("sys.argv", ["script", "--config-path", str(config_path), "--output-path", str(output_path)]):
            matrix_exploder.main()
    
    # Validate successful execution signals.
    assert "✅ Success: Generated 4 permutations" in caplog.text
    assert output_path.exists()
    
    # Verify file content matches expected structural Cartesian product.
    with open(output_path, "r") as f:
        data = json.load(f)
        assert len(data) == 4
        assert {"learning_rate": 0.01, "boundary_map": {"width": 10}} in data
        assert {"learning_rate": 0.001, "boundary_map": {"width": 20}} in data

# Edge Case: The configuration contains scalar root-level values.
# The system must coerce these scalars into single-item lists to maintain
# consistent product logic.
def test_main_with_scalar_values(tmp_path):
    config_path = tmp_path / "config.json"
    output_path = tmp_path / "result.json"
    
    # "learning_rate" is a scalar, forcing the code into the default fallback (else) block.
    config_data = {"learning_rate": 0.01} 
    config_path.write_text(json.dumps(config_data))
    
    with patch("sys.argv", ["script", "--config-path", str(config_path), "--output-path", str(output_path)]):
        matrix_exploder.main()
        
    with open(output_path, "r") as f:
        data = json.load(f)
        # Expected: A list containing one dictionary with the scalar value.
        assert data == [{"learning_rate": 0.01}]