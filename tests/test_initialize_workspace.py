import unittest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the main function
from src.pipeline.initialize_workspace import main, fetch_inputs_from_dropbox

class TestWorkspaceInitializer(unittest.TestCase):

    def setUp(self):
        # Setup common mock paths
        self.repo_path = Path("/tmp/repo")
        self.mock_env = {
            "GITHUB_REF_NAME": "test_branch",
            "DROPBOX_APP_KEY": "key",
            "DROPBOX_APP_SECRET": "secret",
            "DROPBOX_REFRESH_TOKEN": "token",
            "DROPBOX_FOLDER": "/test_folder"
        }

    @patch.dict(os.environ, {"DROPBOX_APP_KEY": ""})
    def test_fetch_inputs_dropbox_missing_creds(self):
        """Ensure missing Dropbox credentials raise EnvironmentError."""
        with self.assertRaises(EnvironmentError):
            fetch_inputs_from_dropbox(Path("/tmp/target"))

    @patch("src.io.download_from_dropbox.CloudIngestor")
    @patch("src.io.dropbox_utils.TokenManager")
    @patch("pathlib.Path.mkdir")
    def test_fetch_inputs_dropbox_success(self, mock_mkdir, mock_tm, mock_ingestor):
        """Test successful Dropbox sync."""
        target_dir = Path("/tmp/target")
        with patch.dict(os.environ, self.mock_env):
            fetch_inputs_from_dropbox(target_dir)
            
            mock_mkdir.assert_called_once()
            mock_ingestor.return_value.sync.assert_called_once()

    @patch("src.pipeline.initialize_workspace.argparse.ArgumentParser.parse_args")
    @patch("builtins.open")
    @patch("json.load")
    @patch("pathlib.Path.rglob")
    @patch("src.pipeline.initialize_workspace.fetch_inputs_from_dropbox")
    @patch("src.pipeline.initialize_workspace.shutil.copy2")
    @patch("src.pipeline.initialize_workspace.TunerState")
    def test_main_success_flow(self, mock_tuner, mock_copy, mock_dropbox, mock_rglob, mock_json, mock_open, mock_args):
        """Test the happy path of the main() function."""
        
        # Setup mocks
        mock_args.return_value = MagicMock(repo_path="/fake/repo", config_path="config.json")
        
        # Mock json content
        task_data = {"pipeline_id": "test_pipeline", "steps": {}, "execution_chain": []}
        manifest_data = {
            "config": "config.json",
            "modules_input_output_folder": "io_folder",
            "execution_chain": [{"order": 1}]
        }
        mock_json.side_effect = [task_data, manifest_data]
        
        # Mock Path.rglob (first call task.json, second call config.json)
        mock_rglob.side_effect = [[Path("task.json")], [Path("config.json")]]
        
        with patch.dict(os.environ, self.mock_env):
            main()
            
        # Assertions
        mock_copy.assert_called() # Ensure config was copied
        mock_tuner.assert_called() # Ensure state initialized
        
    @patch("src.pipeline.initialize_workspace.argparse.ArgumentParser.parse_args")
    @patch("builtins.open")
    @patch("json.load")
    @patch("pathlib.Path.rglob")
    def test_main_missing_config_fails(self, mock_rglob, mock_json, mock_open, mock_args):
        """Test that system exits if configuration file is not found."""
        mock_args.return_value = MagicMock(repo_path="/fake/repo", config_path="config.json")
        
        # Return valid task but empty rglob for config
        mock_json.side_effect = [{"pipeline_id": "p1"}, {"config": "missing.json"}]
        mock_rglob.side_effect = [[Path("task.json")], []] # Config not found
        
        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 1)

if __name__ == "__main__":
    unittest.main()