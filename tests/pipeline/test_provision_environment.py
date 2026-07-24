import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

# Import the main script execution pathway
from src.pipeline.provision_environment import main


class TestProvisionEnvironment(unittest.TestCase):

    def setUp(self):
        # Establish reusable pristine metadata payloads used to simulate
        # standard task manifests and environment configurations.
        self.valid_task_data = {
            "library_repository_url": "https://github.com/org/repo.git",
            "version_tag": "v1.0.0",
            "pipeline_id": "ACE_TRACK_ALPHA"
        }
        self.valid_manifest_data = {
            "setup_script": "scripts/provision_nodes.sh"
        }

    # -------------------------------------------------------------------------
    # Stage 1: Workspace Integrity & Parser Robustness
    # -------------------------------------------------------------------------

    @patch("pathlib.Path.exists")
    def test_main_missing_task_json(self, mock_exists):
        # We verify the environment entrypoint enforces structural presence.
        # If the root workspace lacks a task.json manifest, the system halts.
        mock_exists.return_value = False

        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 1)

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    def test_main_corrupt_json_format(self, mock_json_load, mock_file_open, mock_exists):
        # Malformed configuration manifests represent a failure to comply with 
        # contract definitions. We simulate a parser exception and verify
        # that the system exits with a non-zero status.
        mock_exists.return_value = True
        mock_json_load.side_effect = json.JSONDecodeError("Malformed JSON unexpected token", doc="", pos=0)

        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 1)

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    def test_main_missing_vital_metadata(self, mock_json_load, mock_file_open, mock_exists):
        # A valid JSON schema is insufficient; the schema must also contain 
        # required deployment keys (pipeline_id). We verify that parsing 
        # incomplete metadata triggers an abort.
        mock_exists.return_value = True
        mock_json_load.return_value = {
            "library_repository_url": "https://github.com/org/repo.git",
            "version_tag": "v1.0.0"
        }

        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 1)

    # -------------------------------------------------------------------------
    # Stage 2: Dependency Resolution (Git Clone Lifecycle)
    # -------------------------------------------------------------------------

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    @patch("subprocess.run")
    def test_main_clone_command_fails(self, mock_sub_run, mock_json_load, mock_file_open, mock_exists):
        # Environment provisioning relies on external git resources. 
        # If the transport layer (git clone) fails, the pipeline must recognize 
        # the non-zero exit code and terminate immediately.
        mock_exists.return_value = True
        mock_json_load.return_value = self.valid_task_data
        
        mock_result = MagicMock()
        mock_result.returncode = 128
        mock_sub_run.return_value = mock_result

        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 1)

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    @patch("subprocess.run")
    def test_main_clone_succeeds_but_missing_git_directory(self, mock_sub_run, mock_json_load, mock_file_open, mock_exists):
        # Even if the git command reports success, we perform an integrity 
        # audit for the presence of the '.git' directory. Absent this 
        # directory, the repository is deemed incomplete/unverified.
        def exists_side_effect(path_obj=None, *args, **kwargs):
            return "task.json" in str(path_obj)
        mock_exists.side_effect = exists_side_effect
        
        mock_json_load.return_value = self.valid_task_data
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_sub_run.return_value = mock_result

        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 1)

    # -------------------------------------------------------------------------
    # Stage 3: Execution & Manifest Lifecycle
    # -------------------------------------------------------------------------

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.rglob")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    @patch("subprocess.run")
    def test_main_no_manifest_matches_found(self, mock_sub_run, mock_json_load, mock_file_open, mock_rglob, mock_mkdir, mock_exists):
        # After successful cloning, the system attempts to resolve local execution 
        # manifests via glob pattern matching. If no manifests are resolved, 
        # the provisioning process cannot proceed.
        mock_exists.return_value = True
        mock_json_load.return_value = self.valid_task_data
        mock_sub_run.return_value = MagicMock(returncode=0)
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
        # Some manifests are purely informational. If a manifest is resolved but
        # does not define a 'setup_script', the system exits gracefully (No-Op),
        # as there is no executable payload to initialize.
        mock_exists.return_value = True
        mock_json_load.side_effect = [self.valid_task_data, {}]
        mock_sub_run.return_value = MagicMock(returncode=0)
        mock_rglob.return_value = [Path("repositories/payload_library/ACE_TRACK_ALPHA.json")]

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
        # We verify that during the dynamic execution phase, should the 
        # provisioning script exit with a non-zero code (e.g., 255), the 
        # orchestrator correctly captures this failure and propagates the status.
        mock_exists.return_value = True
        mock_json_load.side_effect = [self.valid_task_data, self.valid_manifest_data]
        mock_sub_run.return_value = MagicMock(returncode=0)
        mock_rglob.return_value = [Path("repositories/payload_library/ACE_TRACK_ALPHA.json")]

        mock_process = MagicMock()
        mock_process.stdout = ["Initializing variables...\n", "Error: Missing network node dependency!\n"]
        mock_process.wait.return_value = 255
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
        # The 'Happy Path' integration test: We simulate a full provisioning 
        # lifecycle including repository cloning, manifest resolution, 
        # and successful runtime script execution.
        mock_exists.return_value = True
        mock_json_load.side_effect = [self.valid_task_data, self.valid_manifest_data]
        mock_sub_run.return_value = MagicMock(returncode=0)
        mock_rglob.return_value = [Path("repositories/payload_library/ACE_TRACK_ALPHA.json")]

        mock_process = MagicMock()
        mock_process.stdout = ["Node provisioning start...\n", "Cluster configuration: Complete.\n"]
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        main()
        
        # Verify Git orchestration parameters (including check=False matching production signature)
        mock_sub_run.assert_any_call(
            ["git", "clone", "--depth", "1", "--branch", "v1.0.0", "https://github.com/org/repo.git", "repositories/payload_library"],
            check=False
        )
        # Verify script execution
        mock_popen.assert_called_once()


if __name__ == "__main__":
    unittest.main()