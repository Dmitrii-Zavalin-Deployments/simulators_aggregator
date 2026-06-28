# tests/pipeline/test_generate_execution_cmd.py

import os
import json
import pytest
from unittest.mock import patch
from src.pipeline.generate_execution_cmd import main

# ==============================================================================
# Narrative: Pipeline Generation Logic Tests
# ==============================================================================

def test_main_dormant_state(tmp_path, caplog, capsys):
    """
    Narrative: Verify that when a 'dormant.flag' file exists containing 
    the correct status string, the script gracefully exits with shutdown commands.
    """
    # We define the path to the flag file.
    dormant_file = tmp_path / "dormant.flag"
    dormant_file.write_text("STATUS: DORMANT")
    
    # We change the working directory to the temp path so the script finds the flag.
    os.chdir(tmp_path)
    
    # We set arguments pointing to a dummy file.
    with patch("sys.argv", ["script", "--state-file", "dummy.json"]):
        with pytest.raises(SystemExit) as e:
            main()
        
    # The script should exit with status 0.
    assert e.value.code == 0
    
    # We verify the logs show the state transition.
    assert "Pipeline state is DORMANT" in caplog.text
    
    # We verify the stdout contains the specific shutdown commands.
    captured = capsys.readouterr()
    assert "echo '🏁 Notice:" in captured.out


def test_main_missing_state_file(tmp_path, caplog, capsys):
    """
    Narrative: Verify that providing a non-existent path to the state file
    results in an error log and a non-zero exit code.
    """
    missing_file = tmp_path / "non_existent.json"
    
    with patch("sys.argv", ["script", "--state-file", str(missing_file)]):
        with pytest.raises(SystemExit) as e:
            main()
            
    # The script should exit with status 1 due to the file error.
    assert e.value.code == 1
    
    # We verify the error log was generated.
    assert "not located" in caplog.text
    
    # We verify the error echo command was printed to stdout.
    captured = capsys.readouterr()
    assert "❌ ERROR" in captured.out


def test_main_valid_execution(tmp_path, caplog, capsys):
    """
    Narrative: Verify the core logic of command generation. This covers
    JSON parsing, URL replacement (git to https), and command string construction.
    """
    # We construct a mock state.json file.
    state_file = tmp_path / "state.json"
    data = {
        "task_details": [
            {
                "repository_url": "git@github.com:user/sim.git",
                "order": 1
            }
        ]
    }
    state_file.write_text(json.dumps(data))
    
    # We run the main function with our temp state file.
    with patch("sys.argv", ["script", "--state-file", str(state_file)]):
        main()
    
    # We capture the output command string.
    captured = capsys.readouterr()
    
    # Assertions:
    # 1. URL was replaced from git@ to https://
    # 2. Output contains the execution path.
    # 3. Log confirms task parsing.
    assert "https://github.com/user/sim" in captured.out
    assert "Adding task for repository: sim" in caplog.text


def test_main_empty_tasks(tmp_path, caplog, capsys):
    """
    Narrative: Verify that valid state files with no defined tasks 
    exit cleanly with a notice.
    """
    # We create a JSON with an empty list.
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"task_details": []}))
    
    with patch("sys.argv", ["script", "--state-file", str(state_file)]):
        with pytest.raises(SystemExit) as e:
            main()
            
    # The script should exit cleanly.
    assert e.value.code == 0
    
    # Verify the warning log.
    assert "no task profiles were configured" in caplog.text
    
    # Verify the user notice.
    captured = capsys.readouterr()
    assert "📋 Notice" in captured.out