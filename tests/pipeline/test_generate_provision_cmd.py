import json
import os
import pytest
import logging
from unittest.mock import patch
from src.pipeline.generate_provision_cmd import main

# ==============================================================================
# Narrative: Provisioning Command Generation Logic Tests
# ==============================================================================

@pytest.fixture
def setup_environment(tmp_path):
    """
    Creates the scaffolding required for a successful execution:
    - A state.json file
    - A config_combinations_array.json matrix file
    """
    base_dir = tmp_path / "pipeline"
    base_dir.mkdir()
    
    state_file = base_dir / "state.json"
    state_file.write_text(json.dumps({
        "task_details": [
            {"repository_url": "git@github.com:user/sim.git", "version_tag": "v1.0", "order": 1}
        ]
    }))
    
    combinations_file = base_dir / "config_combinations_array.json"
    combinations_file.write_text(json.dumps([{"param": "val1"}, {"param": "val2"}]))
    
    return str(state_file)

def test_missing_state_file(caplog):
    # We attempt to run the script with a path that does not exist.
    # We expect the script to log an ERROR and exit with code 1.
    caplog.set_level(logging.ERROR)
    
    with patch("sys.argv", ["script", "--state-file", "nonexistent.json"]):
        with pytest.raises(SystemExit) as e:
            main()
    
    assert e.value.code == 1
    assert "not located" in caplog.text

def test_missing_matrix_file(tmp_path, caplog):
    # We provide a valid state file, but ensure the adjacent matrix file is missing.
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"task_details": []}))
    
    caplog.set_level(logging.ERROR)
    
    with patch("sys.argv", ["script", "--state-file", str(state_file)]):
        with pytest.raises(SystemExit) as e:
            main()
            
    assert e.value.code == 1
    assert "Matrix file missing" in caplog.text

def test_dormant_state_on_empty_matrix(tmp_path, caplog):
    # We provide an empty list in the matrix file.
    # The script should detect this as 'exhausted', create a dormant.flag, and exit 0.
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"task_details": []}))
    
    combinations_file = tmp_path / "config_combinations_array.json"
    combinations_file.write_text(json.dumps([]))
    
    caplog.set_level(logging.WARNING)
    
    with patch("sys.argv", ["script", "--state-file", str(state_file)]):
        with pytest.raises(SystemExit) as e:
            main()
            
    assert e.value.code == 0
    assert "All configuration variations exhausted" in caplog.text
    assert os.path.exists("dormant.flag")

def test_successful_command_generation(setup_environment, capsys, caplog):
    # We execute the script with valid inputs and assert the generated bash commands.
    caplog.set_level(logging.INFO)
    
    with patch("sys.argv", ["script", "--state-file", setup_environment]):
        main()
    
    captured = capsys.readouterr()
    
    # 1. Assert bash command integrity
    assert "git clone https://github.com/user/sim.git" in captured.out
    assert "git checkout v1.0" in captured.out
    assert "cp" in captured.out
    assert "diff" in captured.out  # Integrity check loop
    
    # 2. Assert logging
    assert "Loaded 2 configuration variations" in caplog.text
    assert "Popped next configuration" in caplog.text
    assert "Generation complete" in caplog.text

def test_sorting_logic(tmp_path, capsys):
    # We ensure tasks with different 'order' values are sorted correctly.
    # Task B (order 1) should appear before Task A (order 2).
    base_dir = tmp_path / "pipeline"
    base_dir.mkdir()
    
    state_file = base_dir / "state.json"
    state_file.write_text(json.dumps({
        "task_details": [
            {"repository_url": "git@github.com:user/A.git", "version_tag": "v1", "order": 2},
            {"repository_url": "git@github.com:user/B.git", "version_tag": "v1", "order": 1}
        ]
    }))
    
    combinations_file = base_dir / "config_combinations_array.json"
    combinations_file.write_text(json.dumps([{"cfg": "data"}]))
    
    with patch("sys.argv", ["script", "--state-file", str(state_file)]):
        main()
        
    captured = capsys.readouterr()
    
    # Verify Task B index is less than Task A index in the string
    assert captured.out.find("B") < captured.out.find("A")