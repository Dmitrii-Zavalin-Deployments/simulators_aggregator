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
    Narrative: Verify that when a 'dormant.flag' file exists, the script
    gracefully exits with shutdown commands.
    """
    dormant_file = tmp_path / "dormant.flag"
    dormant_file.write_text("STATUS: DORMANT")
    caplog.set_level(logging.INFO)
    
    with patch("sys.argv", ["script", "--state-file", "dummy.json"]):
        with pytest.raises(SystemExit) as e:
            main()
        
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
    
    state_file = tmp_path / "state.json"
    data = {
        "task_details": [
            {"repository_url": "git@github.com:user/sim.git", "order": 1}
        ]
    }
    state_file.write_text(json.dumps(data))
    
    with patch("sys.argv", ["script", "--state-file", str(state_file)]):
        main()
    
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
    
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"task_details": []}))
    
    with patch("sys.argv", ["script", "--state-file", str(state_file)]):
        with pytest.raises(SystemExit) as e:
            main()
            
    assert e.value.code == 0
    assert "no task profiles were configured" in caplog.text
    captured = capsys.readouterr()
    assert "📋 Notice" in captured.out


def test_main_sorting_and_protocol_handling(tmp_path, caplog, capsys):
    """
    Narrative: Verify sorting order and correct normalization of repository paths.
    """
    caplog.set_level(logging.INFO)
    
    state_file = tmp_path / "state.json"
    data = {
        "task_details": [
            {"repository_url": "git@github.com:org/repo_B.git", "order": 2},
            {"repository_url": "https://github.com/org/repo_A.git", "order": 1}
        ]
    }
    state_file.write_text(json.dumps(data))
    
    with patch("sys.argv", ["script", "--state-file", str(state_file)]):
        main()
    
    captured = capsys.readouterr()
    
    # Verify sorting: Repo A (order 1) should appear before Repo B (order 2)
    assert captured.out.find("repo_A") < captured.out.find("repo_B")
    
    # Asserting local path normalization (not the original URL)
    assert "repositories/repo_A/src/main.py" in captured.out


def test_main_entry_point():
    """
    Narrative: Simulate execution of the main block using absolute pathing.
    """
    # Calculate absolute path to the production script
    test_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(test_dir))
    script_path = os.path.join(project_root, "src", "pipeline", "generate_execution_cmd.py")
    
    test_args = ["script", "--state-file", "non_existent.json"]
    
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            # Execute using the resolved absolute path
            runpy.run_path(script_path, run_name="__main__")
            
    assert e.value.code == 1