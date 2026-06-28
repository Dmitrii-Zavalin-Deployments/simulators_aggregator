import os
import json
import runpy
import sys
import logging
import pytest
from unittest.mock import patch
from src.pipeline.generate_execution_cmd import main

# ==============================================================================
# Narrative: Pipeline Generation Logic Tests
# ==============================================================================

@pytest.fixture(autouse=True)
def sandbox_environment(monkeypatch, tmp_path):
    # We enforce environment isolation by forcing all tests into a temporary sandbox.
    # This prevents the production 'dormant.flag' from interfering with tests.
    monkeypatch.chdir(tmp_path)


def test_main_dormant_state(tmp_path, caplog, capsys):
    # We simulate a DORMANT pipeline state by writing the status indicator to a local file.
    #     dormant.flag content = "STATUS: DORMANT"
    dormant_file = tmp_path / "dormant.flag"
    dormant_file.write_text("STATUS: DORMANT")
    caplog.set_level(logging.INFO)
    
    # We execute the main function with a dummy state file.
    # We expect a graceful exit (code 0) and the specific dormant-state log.
    with patch("sys.argv", ["script", "--state-file", "dummy.json"]):
        with pytest.raises(SystemExit) as e:
            main()
        
    assert e.value.code == 0
    assert "Pipeline state is DORMANT" in caplog.text
    captured = capsys.readouterr()
    assert "echo '🏁 Notice:" in captured.out


def test_main_missing_state_file(tmp_path, caplog, capsys):
    # We simulate an error condition where the provided state file path does not exist.
    # We define the path:
    missing_file = tmp_path / "non_existent.json"
    caplog.set_level(logging.INFO)
    
    # When main() runs without a valid state file, it must raise a SystemExit with code 1.
    with patch("sys.argv", ["script", "--state-file", str(missing_file)]):
        with pytest.raises(SystemExit) as e:
            main()
            
    assert e.value.code == 1
    assert "not located" in caplog.text
    captured = capsys.readouterr()
    assert "❌ ERROR" in captured.out


def test_main_valid_execution(tmp_path, caplog, capsys):
    # We define a valid JSON state for a simulation task with:
    #     repo_url = "git@github.com:user/sim.git"
    #     order = 1
    state_file = tmp_path / "state.json"
    data = {
        "task_details": [
            {"repository_url": "git@github.com:user/sim.git", "order": 1}
        ]
    }
    state_file.write_text(json.dumps(data))
    caplog.set_level(logging.INFO)
    
    # We execute the pipeline generator.
    # We expect the generator to map the repository to the local path and log the action.
    with patch("sys.argv", ["script", "--state-file", str(state_file)]):
        main()
    
    captured = capsys.readouterr()
    assert 'repositories/sim/src/main.py' in captured.out
    assert "Adding task for repository: sim" in caplog.text


def test_main_empty_tasks(tmp_path, caplog, capsys):
    # We define a valid state file that contains no task definitions:
    #     task_details = []
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"task_details": []}))
    caplog.set_level(logging.INFO)
    
    # We expect an exit code of 0 (success) because an empty configuration is valid, 
    # but results in no tasks being scheduled.
    with patch("sys.argv", ["script", "--state-file", str(state_file)]):
        with pytest.raises(SystemExit) as e:
            main()
            
    assert e.value.code == 0
    assert "no task profiles were configured" in caplog.text
    captured = capsys.readouterr()
    assert "📋 Notice" in captured.out


def test_main_sorting_and_protocol_handling(tmp_path, caplog, capsys):
    # We define two tasks in reverse order to test the sorting mechanism:
    #     Task A: URL https://... (order 1)
    #     Task B: URL git@... (order 2)
    state_file = tmp_path / "state.json"
    data = {
        "task_details": [
            {"repository_url": "git@github.com:org/repo_B.git", "order": 2},
            {"repository_url": "https://github.com/org/repo_A.git", "order": 1}
        ]
    }
    state_file.write_text(json.dumps(data))
    caplog.set_level(logging.INFO)
    
    # Upon execution, the generator must sort by order (A before B).
    with patch("sys.argv", ["script", "--state-file", str(state_file)]):
        main()
    
    captured = capsys.readouterr()
    
    # The generated command string must reflect the sorted order:
    #     repo_A should appear before repo_B
    assert captured.out.find("repo_A") < captured.out.find("repo_B")
    
    # Asserting local path normalization (not the original URL)
    assert "repositories/repo_A/src/main.py" in captured.out


def test_main_entry_point():
    # We simulate direct module execution using runpy.
    # First, we resolve the absolute path to the production script to bypass path issues:
    test_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(test_dir))
    script_path = os.path.join(project_root, "src", "pipeline", "generate_execution_cmd.py")
    
    # We define the CLI arguments:
    test_args = ["script", "--state-file", "non_existent.json"]
    
    # We execute the script in the '__main__' namespace to trigger the entry point block:
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            runpy.run_path(script_path, run_name="__main__")
            
    # The expected outcome is a termination due to the non-existent state file (code 1).
    assert e.value.code == 1