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
    # We define the base directory for our test pipeline infrastructure:
    base_dir = tmp_path / "pipeline"
    base_dir.mkdir()
    
    # We create a state.json file containing a task definition:
    #     task = {"repository_url": "git@github.com:user/sim.git", "version_tag": "v1.0", "order": 1}
    state_file = base_dir / "state.json"
    state_file.write_text(json.dumps({
        "task_details": [
            {"repository_url": "git@github.com:user/sim.git", "version_tag": "v1.0", "order": 1}
        ]
    }))
    
    # We define the matrix of configuration combinations:
    #     combinations = [{"param": "val1"}, {"param": "val2"}]
    combinations_file = base_dir / "config_combinations_array.json"
    combinations_file.write_text(json.dumps([{"param": "val1"}, {"param": "val2"}]))
    
    return str(state_file)

def test_missing_state_file(caplog):
    # We define a scenario where the required state file is missing from the file system.
    # We expect the main() function to log an error and trigger a SystemExit with code 1.
    caplog.set_level(logging.ERROR)
    
    with patch("sys.argv", ["script", "--state-file", "nonexistent.json"]):
        with pytest.raises(SystemExit) as e:
            main()
    
    # We assert that the process exited with the error code:
    assert e.value.code == 1
    # We verify the logged error message:
    assert "not located" in caplog.text

def test_missing_matrix_file(tmp_path, caplog):
    # We create a valid state file, but omit the required matrix configuration file.
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"task_details": []}))
    
    # We expect the generator to fail to locate the matrix, logging an error and exiting code 1.
    caplog.set_level(logging.ERROR)
    
    with patch("sys.argv", ["script", "--state-file", str(state_file)]):
        with pytest.raises(SystemExit) as e:
            main()
            
    assert e.value.code == 1
    assert "Matrix file missing" in caplog.text

def test_dormant_state_on_empty_matrix(tmp_path, caplog):
    # We provide a valid state file, but an empty list for the configuration matrix.
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"task_details": []}))
    
    combinations_file = tmp_path / "config_combinations_array.json"
    combinations_file.write_text(json.dumps([]))
    
    # We expect the system to enter a 'DORMANT' state because no work remains.
    # The expected outcome is a clean exit (code 0) and creation of a dormant.flag file.
    caplog.set_level(logging.WARNING)
    
    with patch("sys.argv", ["script", "--state-file", str(state_file)]):
        with pytest.raises(SystemExit) as e:
            main()
            
    assert e.value.code == 0
    assert "All configuration variations exhausted" in caplog.text
    assert os.path.exists("dormant.flag")

def test_successful_command_generation(setup_environment, capsys, caplog):
    # We execute the script using valid input files defined in the setup_environment fixture.
    caplog.set_level(logging.INFO)
    
    with patch("sys.argv", ["script", "--state-file", setup_environment]):
        main()
    
    # We capture the generated output (commands) and log events:
    captured = capsys.readouterr()
    
    # We verify that the generated commands contain the correct Git and file operations:
    #     1. Cloning logic
    #     2. Checkout logic
    #     3. Configuration injection (cp)
    #     4. Integrity audit (diff)
    assert "git clone https://github.com/user/sim.git" in captured.out
    assert "git checkout v1.0" in captured.out
    assert "cp" in captured.out
    assert "diff" in captured.out
    
    # We verify the progression logs are generated correctly:
    assert "Loaded 2 configuration variations" in caplog.text
    assert "Popped next configuration" in caplog.text
    assert "Generation complete" in caplog.text

def test_sorting_logic(tmp_path, capsys):
    # We define a scenario with unsorted task orders:
    #     Task A: order 2
    #     Task B: order 1
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
    
    # We execute the main function:
    with patch("sys.argv", ["script", "--state-file", str(state_file)]):
        main()
        
    # We verify that the command string respects the sort order (Task B < Task A):
    captured = capsys.readouterr()
    assert captured.out.find("B") < captured.out.find("A")