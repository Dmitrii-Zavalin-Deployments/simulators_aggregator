import os
import json
import runpy
import sys
import logging
import pytest
from unittest.mock import patch
from src.pipeline.generate_execution_cmd import main

# ==============================================================================
# Narrative: Pipeline Generation Logic Tests with Automated Sandbox Isolation
# ==============================================================================

@pytest.fixture(autouse=True)
def sandbox_environment(monkeypatch, tmp_path):
    """
    Enforces a strict local sandbox for every test execution block.
    Automatically moves the current working directory away from the project root
    so that tests never accidentally see or mutate the production 'dormant.flag'.
    """
    monkeypatch.chdir(tmp_path)


def test_main_dormant_state(tmp_path, caplog, capsys):
    """
    Narrative: Verify that when a 'dormant.flag' file exists in the context directory, 
    the script gracefully exits with shutdown commands.
    """
    # 1. Setup: Create localized dormant flag and force INFO level logging
    dormant_file = tmp_path / "dormant.flag"
    dormant_file.write_text("STATUS: DORMANT")
    caplog.set_level(logging.INFO)
    
    # 2. Execution
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


def test_main_sorting_and_protocol_handling(tmp_path, caplog, capsys):
    """
    Narrative: Verify that multiple tasks are sorted by order and that 
    URLs without 'git@github.com' are processed without modification.
    """
    caplog.set_level(logging.INFO)
    
    # 1. Setup: Two tasks, reversed order, one with non-git URL
    state_file = tmp_path / "state.json"
    data = {
        "task_details": [
            {"repository_url": "git@github.com:org/repo_B.git", "order": 2},
            {"repository_url": "https://github.com/org/repo_A.git", "order": 1}
        ]
    }
    state_file.write_text(json.dumps(data))
    
    # 2. Execution
    with patch("sys.argv", ["script", "--state-file", str(state_file)]):
        main()
    
    # 3. Assertions
    captured = capsys.readouterr()
    
    # Verify sorting: Repo A (order 1) should appear before Repo B (order 2)
    assert captured.out.find("repo_A") < captured.out.find("repo_B")
    
    # Verify non-replacement: 'https' should remain 'https'
    assert "https://github.com/org/repo_A" in captured.out


def test_main_entry_point():
    """
    Narrative: Simulate execution of the main block to reach 100% coverage.
    Explicitly provides `run_name="__main__"` to simulate standard module execution.
    """
    test_args = ["script", "--state-file", "non_existent.json"]
    
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            # Setting run_name explicitly ensures the __name__ == "__main__" check evaluates to True
            runpy.run_path("src/pipeline/generate_execution_cmd.py", run_name="__main__")
            
    # In a clean sandbox folder without a flag or file, the production script returns exit code 1
    assert e.value.code == 1