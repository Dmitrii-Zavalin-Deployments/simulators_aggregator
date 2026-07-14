import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Import the main script execution pathway
from src.pipeline.provision_environment import main


class TestProvisionEnvironment(unittest.TestCase):

    def setUp(self):
        # Establish reusable pristine metadata payloads
        self.valid_task_data = {
            "library_repository_url": "https://github.com/org/repo.git",
            "version_tag": "v1.0.0",
            "pipeline_id": "ACE_TRACK_ALPHA"
        }
        self.valid_manifest_data = {
            "setup_script": "scripts/provision_nodes.sh"
        }

    @patch("pathlib.Path.exists")
    def test_main_missing_task_json(self, mock_exists):
        """Branch: task.json is completely absent at the workspace root."""
        mock_exists.return_value = False

        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 1)

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    def test_main_corrupt_json_format(self, mock_json_load, mock_file_open, mock_exists):
        """Branch: task.json exists but contains broken/malformed structures."""
        mock_exists.return_value = True
        mock_json_load.side_effect = Exception("Malformed JSON unexpected token")

        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 1)

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    def test_main_missing_vital_metadata(self, mock_json_load, mock_file_open, mock_exists):
        """Branch: task.json parsed successfully but lacks required deployment keys."""
        mock_exists.return_value = True
        # Missing 'pipeline_id'
        mock_json_load.return_value = {
            "library_repository_url": "https://github.com/org/repo.git",
            "version_tag": "v1.0.0"
        }

        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 1)

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    @patch("subprocess.run")
    def test_main_clone_command_fails(self, mock_sub_run, mock_json_load, mock_file_open, mock_exists):
        """Branch: The git clone subcommand exits with a non-zero status code."""
        # Setup Path.exists to trigger the 'rm -rf' path and simulate valid task mapping
        def exists_side_effect(path_obj):
            return True  # Both task.json and old repo directory exist
        mock_exists.side_effect = exists_side_effect
        
        mock_json_load.return_value = self.valid_task_data
        
        # Mock git clone return failure status code
        mock_result = MagicMock()
        mock_result.returncode = 128
        mock_sub_run.return_value = mock_result

        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 1)
        # Ensure the cleanup 'rm -rf' path execution was triggered
        self.assertEqual(mock_sub_run.call_count, 2)

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    @patch("subprocess.run")
    def test_main_clone_succeeds_but_missing_git_directory(self, mock_sub_run, mock_json_load, mock_file_open, mock_exists):
        """Branch: git clone returned zero, but verification .git folder doesn't exist."""
        def exists_side_effect(path_obj):
            # Simulate task.json exists, old repo clean doesn't exist, but .git fails validation check
            if "task.json" in str(path_obj):
                return True
            return False
        mock_exists.side_effect = exists_side_effect
        
        mock_json_load.return_value = self.valid_task_data
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_sub_run.return_value = mock_result

        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 1)

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.rglob")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    @patch("subprocess.run")
    def test_main_no_manifest_matches_found(self, mock_sub_run, mock_json_load, mock_file_open, mock_rglob, mock_mkdir, mock_exists):
        """Branch: Library cloned but rglob file target pattern match list is empty."""
        def exists_side_effect(path_obj):
            if "task.json" in str(path_obj) or ".git" in str(path_obj):
                return True
            return False
        mock_exists.side_effect = exists_side_effect
        mock_json_load.return_value = self.valid_task_data
        mock_sub_run.return_value = MagicMock(returncode=0)
        
        # Force empty lookup sequence array matching
        mock_rglob.return_value = []

        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 1)

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.rglob")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    @patch("subprocess.run")
    def test_main_manifest_has_no_explicit_setup_script(self, mock_sub_run, mock_json_load, mock_file_open, mock_rglob, mock_mkdir, mock_exists):
        """Branch: Manifest resolved but contains no execution scripts (Warning Path)."""
        def exists_side_effect(path_obj):
            return "task.json" in str(path_obj) or ".git" in str(path_obj)
        mock_exists.side_effect = exists_side_effect
        
        # Sequence return values: 1st call loads task configuration, 2nd call loads manifest configuration
        mock_json_load.side_effect = [self.valid_task_data, {}]
        mock_sub_run.return_value = MagicMock(returncode=0)
        mock_rglob.return_value = [Path("repositories/payload_library/ACE_TRACK_ALPHA.json")]

        # Executing should pass cleanly without throwing errors or running sub-scripts
        result = main()
        self.assertIsNone(result)

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.rglob")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    @patch("subprocess.run")
    @patch("subprocess.Popen")
    def test_main_setup_script_runtime_fails(self, mock_popen, mock_sub_run, mock_json_load, mock_file_open, mock_rglob, mock_mkdir, mock_exists):
        """Branch: Dynamic execution engine logs Popen streams but script exits with non-zero code."""
        def exists_side_effect(path_obj):
            return "task.json" in str(path_obj) or ".git" in str(path_obj)
        mock_exists.side_effect = exists_side_effect
        
        mock_json_load.side_effect = [self.valid_task_data, self.valid_manifest_data]
        mock_sub_run.return_value = MagicMock(returncode=0)
        mock_rglob.return_value = [Path("repositories/payload_library/ACE_TRACK_ALPHA.json")]

        # Configure Popen instance mock engine output generators
        mock_process = MagicMock()
        mock_process.stdout = ["Initializing variables...\n", "Error: Missing network node dependency!\n"]
        mock_process.wait.return_value = 255  # Non-zero error crash response
        mock_popen.return_value = mock_process

        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 255)

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.rglob")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    @patch("subprocess.run")
    @patch("subprocess.Popen")
    def test_main_complete_success_flow(self, mock_popen, mock_sub_run, mock_json_load, mock_file_open, mock_rglob, mock_mkdir, mock_exists):
        """Branch: Full integration happy path execution running bash script pipelines perfectly."""
        def exists_side_effect(path_obj):
            return "task.json" in str(path_obj) or ".git" in str(path_obj)
        mock_exists.side_effect = exists_side_effect
        
        mock_json_load.side_effect = [self.valid_task_data, self.valid_manifest_data]
        mock_sub_run.return_value = MagicMock(returncode=0)
        mock_rglob.return_value = [Path("repositories/payload_library/ACE_TRACK_ALPHA.json")]

        # Configure successful setup engine script response loops
        mock_process = MagicMock()
        mock_process.stdout = ["Node provisioning start...\n", "Cluster configuration: Complete.\n"]
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        # Run pipeline validation sequence
        main()
        
        # Verify that our pipeline ran both git clone and inner manifest validations cleanly
        mock_sub_run.assert_called_with(["git", "clone", "--depth", "1", "--branch", "v1.0.0", "https://github.com/org/repo.git", "repositories/payload_library"])
        mock_popen.assert_called_once()


if __name__ == "__main__":
    unittest.main()