import unittest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the main orchestration and ingestion functions.
from src.pipeline.initialize_workspace import main, fetch_inputs_from_dropbox

class TestWorkspaceInitializer(unittest.TestCase):

    # -------------------------------------------------------------------------
    # Environment Initialization
    # -------------------------------------------------------------------------
    
    def setUp(self):
        # We define a standard workspace environment for our test suite.
        # The repo_path serves as our root, while mock_env provides the
        # authentication keys required for secure Dropbox data retrieval.
        self.repo_path = Path("/tmp/repo")
        self.mock_env = {
            "GITHUB_REF_NAME": "test_branch",
            "DROPBOX_APP_KEY": "key",
            "DROPBOX_APP_SECRET": "secret",
            "DROPBOX_REFRESH_TOKEN": "token",
            "DROPBOX_FOLDER": "/test_folder"
        }

    # -------------------------------------------------------------------------
    # Dropbox Integration Tests
    # -------------------------------------------------------------------------

    # Logic: A zero-default policy dictates that if credentials are absent,
    # the system must raise an EnvironmentError rather than silently failing.
    @patch.dict(os.environ, {"DROPBOX_APP_KEY": ""})
    def test_fetch_inputs_dropbox_missing_creds(self):
        # We simulate a missing key and assert that the retrieval logic halts execution.
        with self.assertRaises(EnvironmentError):
            fetch_inputs_from_dropbox(Path("/tmp/target"))

    # To verify the sync operation, we assume a authenticated environment.
    # We mock the CloudIngestor and TokenManager dependencies to isolate 
    # the sync logic from actual network calls.
    @patch("src.io.download_from_dropbox.CloudIngestor")
    @patch("src.io.dropbox_utils.TokenManager")
    @patch("pathlib.Path.mkdir")
    def test_fetch_inputs_dropbox_success(self, mock_mkdir, mock_tm, mock_ingestor):
        # We proceed to invoke the fetcher and verify that both directory
        # creation and the synchronization trigger are called exactly once.
        target_dir = Path("/tmp/target")
        with patch.dict(os.environ, self.mock_env):
            fetch_inputs_from_dropbox(target_dir)
            
            mock_mkdir.assert_called_once()
            mock_ingestor.return_value.sync.assert_called_once()

    # -------------------------------------------------------------------------
    # Main Pipeline Orchestration Tests
    # -------------------------------------------------------------------------

    # The 'Happy Path' involves parsing the orchestration manifests,
    # copying configuration files, and initializing the TunerState container.
    @patch("src.pipeline.initialize_workspace.argparse.ArgumentParser.parse_args")
    @patch("builtins.open")
    @patch("json.load")
    @patch("pathlib.Path.rglob")
    @patch("src.pipeline.initialize_workspace.fetch_inputs_from_dropbox")
    @patch("src.pipeline.initialize_workspace.shutil.copy2")
    @patch("src.pipeline.initialize_workspace.TunerState")
    def test_main_success_flow(self, mock_tuner, mock_copy, mock_dropbox, mock_rglob, mock_json, mock_open, mock_args):
        # Setup: We mock the CLI arguments and JSON data structures.
        mock_args.return_value = MagicMock(repo_path="/fake/repo", config_path="config.json")
        
        # We provide a task manifest and a configuration manifest to simulate
        # a standard pipeline project structure.
        task_data = {"pipeline_id": "test_pipeline", "steps": {}, "execution_chain": []}
        manifest_data = {
            "config": "config.json",
            "modules_input_output_folder": "io_folder",
            "execution_chain": [{"order": 1}]
        }
        mock_json.side_effect = [task_data, manifest_data]
        
        # We mock rglob to locate the simulated task and config files.
        mock_rglob.side_effect = [[Path("task.json")], [Path("config.json")]]
        
        # Execution: Trigger the main entrypoint.
        with patch.dict(os.environ, self.mock_env):
            main()
            
        # Assertion: Verify the config copy and TunerState initialization occurred.
        mock_copy.assert_called() 
        mock_tuner.assert_called() 
        
    # A robust system must handle missing configuration files gracefully.
    # By mocking rglob to return an empty list, we simulate a file lookup failure.
    @patch("src.pipeline.initialize_workspace.argparse.ArgumentParser.parse_args")
    @patch("builtins.open")
    @patch("json.load")
    @patch("pathlib.Path.rglob")
    def test_main_missing_config_fails(self, mock_rglob, mock_json, mock_open, mock_args):
        # We verify that if the system cannot locate the config file, it exits with code 1.
        mock_args.return_value = MagicMock(repo_path="/fake/repo", config_path="config.json")
        
        mock_json.side_effect = [
            {"pipeline_id": "p1"}, 
            {
                "config": "missing.json", 
                "modules_input_output_folder": "dummy_folder"
            }
        ]
        
        # We return an empty list to represent a failed file search.
        mock_rglob.side_effect = [[Path("task.json")], [], []]
        
        # Final Verification: Expect SystemExit(1)
        with patch("src.pipeline.initialize_workspace.fetch_inputs_from_dropbox"), \
             patch("src.pipeline.initialize_workspace.TunerState"), \
             self.assertRaises(SystemExit) as cm:
             
            main()
            
        self.assertEqual(cm.exception.code, 1)

if __name__ == "__main__":
    unittest.main()