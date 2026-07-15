import unittest
import os
import sys
import builtins
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the main orchestration, ingestion, and self-healing functions.
from src.pipeline.initialize_workspace import (
    main, 
    fetch_inputs_from_dropbox, 
    inspect_and_fix_environment
)

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
        # Safely capture a snapshot of sys.path to prevent side-effects across tests
        self._original_sys_path = list(sys.path)

    def tearDown(self):
        # In-place restoration of sys.path guarantees references are cleanly maintained
        sys.path[:] = self._original_sys_path

    # -------------------------------------------------------------------------
    # Environment Self-Healing Tests
    # -------------------------------------------------------------------------

    # Logic: If the environment is natively healthy, inspect_and_fix_environment
    # must log a success message and return early without altering sys.path.
    def test_inspect_and_fix_environment_native_success(self):
        mock_dropbox = MagicMock()

        # Temporarily inject a mock dropbox into sys.modules to simulate successful import
        with patch.dict("sys.modules", {"dropbox": mock_dropbox}), \
             patch("src.pipeline.initialize_workspace.logger") as mock_logger:
            
            inspect_and_fix_environment()
            
            mock_logger.info.assert_any_call("✅ [ENV] 'dropbox' is natively importable. Path integrity is healthy.")

    # Logic: If native import fails, the function must probe paths, resolve 
    # candidates, append missing search spaces, and succeed on retry.
    @patch("src.pipeline.initialize_workspace.Path.resolve")
    @patch("src.pipeline.initialize_workspace.glob.glob")
    def test_inspect_and_fix_environment_recovery_success(self, mock_glob, mock_resolve):
        original_import = builtins.__import__
        import_attempts = []
        mock_dropbox = MagicMock()

        # Simulate initial failure followed by success after path manipulation
        def mock_import(name, *args, **kwargs):
            if name == "dropbox":
                import_attempts.append(True)
                if len(import_attempts) == 1:
                    raise ImportError("No module named 'dropbox'")
                return mock_dropbox
            return original_import(name, *args, **kwargs)

        # Force glob to return no wildcards, and mock Path.resolve to look like a valid directory
        mock_glob.return_value = []
        mock_resolved_path = MagicMock()
        mock_resolved_path.exists.return_value = True
        mock_resolved_path.__str__.return_value = "/mocked/site-packages"
        mock_resolve.return_value = mock_resolved_path

        # Custom dict to bypass the sys.modules cache specifically for 'dropbox' during lookup
        class SysModulesBypass(dict):
            def __contains__(self, item):
                if item == "dropbox":
                    return False
                return super().__contains__(item)
            def get(self, item, default=None):
                if item == "dropbox":
                    return default
                return super().get(item, default)

        bypass_modules = SysModulesBypass(sys.modules)
        if "dropbox" in bypass_modules:
            del bypass_modules["dropbox"]

        with patch("sys.modules", bypass_modules), \
             patch("builtins.__import__", side_effect=mock_import), \
             patch("src.pipeline.initialize_workspace.logger") as mock_logger:
            
            inspect_and_fix_environment()
            
            self.assertIn("/mocked/site-packages", sys.path)
            mock_logger.warning.assert_any_call("⚠️ [ENV] 'dropbox' not found natively. Initiating automatic system-path repair...")
            mock_logger.info.assert_any_call("✅ [ENV] Self-repair successful: 'dropbox' successfully bound to run context.")

    # Logic: If the package is completely absent, the function must exhaust
    # path searches, fail to import, and log a critical error safely.
    @patch("src.pipeline.initialize_workspace.Path.resolve")
    @patch("src.pipeline.initialize_workspace.glob.glob")
    def test_inspect_and_fix_environment_recovery_failure(self, mock_glob, mock_resolve):
        mock_glob.return_value = []
        mock_resolved_path = MagicMock()
        mock_resolved_path.exists.return_value = True
        mock_resolved_path.__str__.return_value = "/mocked/site-packages"
        mock_resolve.return_value = mock_resolved_path

        # Force persistent failure by mapping 'dropbox' to None in sys.modules
        with patch.dict("sys.modules", {"dropbox": None}), \
             patch("src.pipeline.initialize_workspace.logger") as mock_logger:
            
            inspect_and_fix_environment()
            
            # Assert that the error message contains our expected critical error logs
            error_called = False
            for call in mock_logger.error.call_args_list:
                args, kwargs = call
                if args and "❌ [ENV] CRITICAL: 'dropbox' remains missing after recovery sequence." in args[0]:
                    error_called = True
                    break
            self.assertTrue(error_called, "CRITICAL logging was not called on recovery sequence failure.")

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

    # To verify the sync operation, we assume an authenticated environment.
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