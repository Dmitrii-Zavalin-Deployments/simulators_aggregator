import json
import logging
import pytest
from unittest.mock import patch
from src.pipeline.generate_execution_cmd import main

# ==============================================================================
# Narrative: Pipeline Generation Logic Tests
# ==============================================================================

def test_main_dormant_state(tmp_path, caplog, capsys, monkeypatch):
    """
    Narrative: Verify that when a 'dormant.flag' file exists, the script
    gracefully exits with shutdown commands. Uses monkeypatch for CWD safety.
    """
    # 1. Setup: Create dormant flag and force INFO level logging
    dormant_file = tmp_path / "dormant.flag"
    dormant_file.write_text("STATUS: DORMANT")
    caplog.set_level(logging.INFO)
    
    # 2. Execution: Patch CWD using monkeypatch (automatically reverts after test)
    monkeypatch.chdir(tmp_path)
    
    with patch("sys.argv", ["script", "--state-file", "dummy.json"]):
        with pytest.raises(SystemExit) as e:
            main()
        
    # 3. Assertions
    assert e.value.code == 0
    assert "Pipeline state is DORMANT" in caplog.text
    captured = capsys.readouterr()
    assert "echo '🏁 Notice:" in captured.out


def test_main_missing_state_file(tmp_path, caplog, capsys):
    """
    Narrative: Verify that providing a non-existent path results in an 
    error log and a non-zero exit code.
    """
    caplog.set_level(logging.INFO)
    missing_file = tmp_path / "non_existent.json"
    
    with patch("sys.argv", ["script", "--state-file", str(missing_file)]):
        with pytest.raises(SystemExit) as e:
            main()
            
    assert e.value.code == 1
    assert "not located" in caplog.text
    captured = capsys.readouterr()
    assert "❌ ERROR" in captured.out


def test_main_valid_execution(tmp_path, caplog, capsys):
    """
    Narrative: Verify the core logic of command generation.
    """
    caplog.set_level(logging.INFO)
    
    # 1. Setup: Create a valid JSON state
    state_file = tmp_path / "state.json"
    data = {
        "task_details": [
            {"repository_url": "git@github.com:user/sim.git", "order": 1}
        ]
    }
    state_file.write_text(json.dumps(data))
    
    # 2. Execution
    with patch("sys.argv", ["script", "--state-file", str(state_file)]):
        main()
    
    # 3. Assertions
    captured = capsys.readouterr()
    
    # Verify the local execution path (replacing the URL assertion)
    assert 'repositories/sim/src/main.py' in captured.out
    
    # Verify the logging message
    assert "Adding task for repository: sim" in caplog.text


def test_main_empty_tasks(tmp_path, caplog, capsys):
    """
    Narrative: Verify that valid state files with no tasks exit cleanly.
    """
    caplog.set_level(logging.INFO)
    
    # 1. Setup: Create JSON with empty list
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"task_details": []}))
    
    # 2. Execution
    with patch("sys.argv", ["script", "--state-file", str(state_file)]):
        with pytest.raises(SystemExit) as e:
            main()
            
    # 3. Assertions
    assert e.value.code == 0
    assert "no task profiles were configured" in caplog.text
    captured = capsys.readouterr()
    assert "📋 Notice" in captured.out