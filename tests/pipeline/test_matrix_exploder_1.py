import json
import logging
from unittest.mock import patch

import pytest

from src.pipeline import matrix_exploder

# ==============================================================================
# 1. Logic Verification: The Recursive Exploder
# ==============================================================================

# The `explode_dict` function serves as the computational engine for 
# configuration processing. It recursively traverses input dictionaries
# and computes the Cartesian product of all list-based parameters.

def test_explode_dict_recursion():
    # Scenario: We process a nested structure requiring recursive expansion.
    # Given the input: {"x": [1, 2], "params": {"y": [10, 20]}}
    # The Cartesian product yields 2 * 2 = 4 unique permutations.
    input_map = {
        "x": [1, 2],
        "params": {"y": [10, 20]}
    }
    
    result = matrix_exploder.explode_dict(input_map)
    
    # We verify the cardinality of the generated set and the structural integrity
    # of the resulting permutations.
    assert len(result) == 4
    assert {"x": 1, "params": {"y": 10}} in result
    assert {"x": 2, "params": {"y": 20}} in result

def test_explode_dict_non_dict_input():
    # If the input is not a dictionary (e.g., an integer), it cannot be expanded.
    # The system correctly treats this as an atomic unit and wraps it in a list.
    val = 100
    assert matrix_exploder.explode_dict(val) == [100]

def test_explode_dict_scalar_value():
    # When encountering leaf-node values that are scalars (e.g., integers),
    # the function must treat them as single-item lists to satisfy the 
    # expected Cartesian output schema.
    input_data = {"key": 5}
    assert matrix_exploder.explode_dict(input_data) == [{"key": 5}]

# ==============================================================================
# 2. Main Orchestrator: Failure Modes & Logging
# ==============================================================================

# The `main()` function coordinates filesystem I/O and CLI execution.
# It enforces robust error handling, ensuring that catastrophic failures
# (like missing files or malformed JSON) result in logged errors and 
# standard exit codes (SystemExit(1)).

def test_main_file_not_found(tmp_path, caplog):
    # Scenario: The configuration file path provided via CLI is invalid.
    config_path = tmp_path / "missing.json"
    output_path = tmp_path / "out.json"
    
    with caplog.at_level(logging.ERROR), \
    patch("sys.argv", ["script", "--config-path", str(config_path), "--output-path", str(output_path)]):
    # We expect the system to halt execution immediately.
    with pytest.raises(SystemExit) as exc:
    matrix_exploder.main()
    assert exc.value.code == 1
    
    # We verify the user is notified of the missing dependency.
    assert "❌ Configuration file not found" in caplog.text

def test_main_invalid_json(tmp_path, caplog):
    # Scenario: The input file exists but contains invalid JSON syntax.
    config_path = tmp_path / "bad.json"
    config_path.write_text("{ incomplete json")
    output_path = tmp_path / "out.json"
    
    with caplog.at_level(logging.ERROR), \
    patch("sys.argv", ["script", "--config-path", str(config_path), "--output-path", str(output_path)]):
    with pytest.raises(SystemExit) as exc:
    matrix_exploder.main()
    assert exc.value.code == 1
    
    # We ensure the decoder failure is explicitly reported.
    assert "❌ Failed to parse JSON" in caplog.text

# ==============================================================================
# 3. Integration: Success Path
# ==============================================================================

# We validate the end-to-end integration flow. Given a valid input configuration,
# the system must compute permutations and persist them to the designated output.

def test_main_success_path(tmp_path, caplog):
    # Setup: We define a configuration with two lists of length 2 (2 x 2 = 4 combinations).
    config_path = tmp_path / "config.json"
    output_path = tmp_path / "result.json"
    
    config_data = {
        "learning_rate": [0.01, 0.001],
        "boundary_map": {"width": [10, 20]}
    }
    config_path.write_text(json.dumps(config_data))
    
    with caplog.at_level(logging.INFO), \
    patch("sys.argv", ["script", "--config-path", str(config_path), "--output-path", str(output_path)]):
    matrix_exploder.main()
    
    # We confirm execution success via logs and filesystem persistence.
    assert "✅ Success: Generated 4 permutations" in caplog.text
    assert output_path.exists()
    
    # Verify the contents match the calculated Cartesian product.
    with open(output_path, "r") as f:
        data = json.load(f)
        assert len(data) == 4
        assert {"learning_rate": 0.01, "boundary_map": {"width": 10}} in data
        assert {"learning_rate": 0.001, "boundary_map": {"width": 20}} in data

def test_main_with_scalar_values(tmp_path):
    # Edge Case: The configuration root contains scalar values.
    # The system must coerce these scalars into single-item lists internally
    # to prevent crashes during the expansion logic.
    config_path = tmp_path / "config.json"
    output_path = tmp_path / "result.json"
    
    # "learning_rate" is a scalar, forcing the code into the default fallback (else) block.
    config_data = {"learning_rate": 0.01} 
    config_path.write_text(json.dumps(config_data))
    
    with patch("sys.argv", ["script", "--config-path", str(config_path), "--output-path", str(output_path)]):
        matrix_exploder.main()
        
    with open(output_path, "r") as f:
        data = json.load(f)
        # Expected: A list containing one dictionary with the scalar value preserved.
        assert data == [{"learning_rate": 0.01}]