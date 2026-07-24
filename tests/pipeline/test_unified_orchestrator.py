import json
import unittest
from unittest.mock import MagicMock, patch

# Import the orchestrator main function
from src.pipeline.unified_orchestrator import main


class TestUnifiedOrchestrator(unittest.TestCase):

    def setUp(self):
        # Establish reusable healthy target structures for dependency injection.
        self.args_mock = MagicMock(
            state_file="workspace/state.json",
            log_file="workspace/execution.log"
        )
        
        self.valid_combinations = [
            {"learning_rate": 0.01, "batch_size": 32},
            {"learning_rate": 0.05, "batch_size": 64}
        ]
        
        self.valid_task = {
            "order": "1",
            "repository_url": "git@github.com:org/sim-engine.git",
            "version_tag": "model_v5",
            "input_file_name": "sim_input.csv",
            "output_file_name": "sim_output.csv"
        }
        
        self.valid_state = {
            "task_details": [self.valid_task]
        }

        # Mock database of files for dynamic routing within the virtual filesystem
        self.file_vault = {}

    @staticmethod
    def existence_router(path_obj=None, *args, **kwargs):
        """Centralized fallback router for path existence checks."""
        return False

    def dynamic_open_router(self, file_path, mode="r", *args, **kwargs):
        """A context-aware mock file provider that routes content based on paths."""
        path_str = str(file_path)
        
        # Define mock file behavior
        mock_file = MagicMock()

        if "r" in mode:
            if path_str in self.file_vault:
                content = self.file_vault[path_str]
            else:
                content = "{}"
                
            mock_file.read.return_value = content
            # Support direct iteration over json loading if needed
            if path_str.endswith(".json"):
                mock_file.read.return_value = content

        elif "w" in mode or "a" in mode:
            def write_side_effect(written_data):
                self.file_vault[path_str] = written_data
                return len(written_data)
            mock_file.write.side_effect = write_side_effect
            
        # Support context manager protocol
        mock_file.__enter__.return_value = mock_file
        return mock_file

    # ==========================================
    # PRE-FLIGHT AND SYSTEM DORMANCY GATES
    # ==========================================

    # The orchestrator utilizes a dormancy gate mechanism to pause operations 
    # during maintenance or system cooldowns. If the dormancy flag is set, 
    # the pipeline must treat this as an expected exit, not a failure.

    @patch("src.pipeline.unified_orchestrator.argparse.ArgumentParser.parse_args")
    @patch("src.pipeline.unified_orchestrator.os.path.exists")
    @patch("src.pipeline.unified_orchestrator.open")
    def test_preflight_dormant_flag_terminates_pipeline(self, mock_open_func, mock_exists, mock_parse_args):
        """Branch: dormant.flag is active and contains DORMANT status -> Clean Exit 0."""
        mock_parse_args.return_value = self.args_mock
        
        # Route path existence checks to trigger the dormant gate.
        mock_exists.side_effect = lambda path: str(path) == "dormant.flag"
        self.file_vault["dormant.flag"] = "STATUS: DORMANT\n"
        mock_open_func.side_effect = self.dynamic_open_router

        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 0)

    @patch("src.pipeline.unified_orchestrator.argparse.ArgumentParser.parse_args")
    @patch("src.pipeline.unified_orchestrator.os.path.exists")
    @patch("src.pipeline.unified_orchestrator.open")
    @patch("pathlib.Path.exists")
    def test_preflight_inactive_dormant_flag_continues(self, mock_path_exists, mock_open_func, mock_exists, mock_parse_args):
        # If the dormant file exists but is not set to 'DORMANT', the pipeline 
        # must attempt to proceed, eventually failing at the next state-validation gate.
        mock_parse_args.return_value = self.args_mock
        mock_exists.side_effect = lambda path: str(path) == "dormant.flag"
        mock_path_exists.return_value = False 
        
        self.file_vault["dormant.flag"] = "STATUS: ACTIVE_RUNNING\n"
        mock_open_func.side_effect = self.dynamic_open_router

        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 1)

    # ==========================================
    # FILE EXISTENCE AND STRUCTURAL PARSE GATES
    # ==========================================

    # Before execution, the orchestrator performs a structural validation of 
    # configuration files. It mandates the presence of 'state.json' and 
    # 'config_combinations_array.json'. Failure to locate or parse these files 
    # is a terminal condition.

    @patch("src.pipeline.unified_orchestrator.argparse.ArgumentParser.parse_args")
    @patch("src.pipeline.unified_orchestrator.os.path.exists")
    @patch("pathlib.Path.exists")
    def test_missing_state_file_raises_critical(self, mock_path_exists, mock_exists, mock_parse_args):
        """Branch: State blueprint map file is physically missing."""
        mock_parse_args.return_value = self.args_mock
        mock_exists.side_effect = self.existence_router
        mock_path_exists.return_value = False 

        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 1)

    @patch("src.pipeline.unified_orchestrator.argparse.ArgumentParser.parse_args")
    @patch("src.pipeline.unified_orchestrator.os.path.exists")
    @patch("pathlib.Path.exists")
    def test_missing_matrix_combinations_file_raises_critical(self, mock_path_exists, mock_exists, mock_parse_args):
        """Branch: config_combinations_array.json is physically missing."""
        mock_parse_args.return_value = self.args_mock
        mock_exists.side_effect = self.existence_router
        
        # Verify state file existence, but trigger absence of matrix file.
        mock_path_exists.side_effect = lambda *a, **kw: str(mock_path_exists.call_args[0][0]).endswith("state.json") if (mock_path_exists.call_args and len(mock_path_exists.call_args[0]) > 0) else False

        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 1)

    @patch("src.pipeline.unified_orchestrator.argparse.ArgumentParser.parse_args")
    @patch("src.pipeline.unified_orchestrator.os.path.exists")
    @patch("pathlib.Path.exists")
    @patch("src.pipeline.unified_orchestrator.open")
    @patch("src.pipeline.unified_orchestrator.json.load")
    def test_corrupt_combinations_json_raises_critical(self, mock_json_load, mock_open_func, mock_path_exists, mock_exists, mock_parse_args):
        # Data integrity checks are absolute. Invalid JSON syntax results in 
        # an immediate exit.
        mock_parse_args.return_value = self.args_mock
        mock_exists.side_effect = self.existence_router
        mock_path_exists.return_value = True
        
        mock_open_func.side_effect = self.dynamic_open_router
        mock_json_load.side_effect = json.JSONDecodeError("JSON Decode Crash", "", 0)

        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 1)

    @patch("src.pipeline.unified_orchestrator.argparse.ArgumentParser.parse_args")
    @patch("src.pipeline.unified_orchestrator.os.path.exists")
    @patch("pathlib.Path.exists")
    @patch("src.pipeline.unified_orchestrator.open")
    @patch("src.pipeline.unified_orchestrator.json.load")
    def test_empty_combinations_matrix_sets_dormancy_and_exits(self, mock_json_load, mock_open_func, mock_path_exists, mock_exists, mock_parse_args):
        # An empty matrix is not an error; it implies no work is defined.
        # The system must set a dormancy flag and exit cleanly.
        mock_parse_args.return_value = self.args_mock
        mock_exists.side_effect = self.existence_router
        mock_path_exists.return_value = True
        
        mock_open_func.side_effect = self.dynamic_open_router
        mock_json_load.return_value = [] 

        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("STATUS: DORMANT\n", self.file_vault["dormant.flag"])

    @patch("src.pipeline.unified_orchestrator.argparse.ArgumentParser.parse_args")
    @patch("src.pipeline.unified_orchestrator.os.path.exists")
    @patch("pathlib.Path.exists")
    @patch("src.pipeline.unified_orchestrator.open")
    @patch("src.pipeline.unified_orchestrator.json.load")
    def test_corrupt_state_json_raises_critical(self, mock_json_load, mock_open_func, mock_path_exists, mock_exists, mock_parse_args):
        """Branch: Matrix pops safely but state.json blueprint contains invalid structures."""
        mock_parse_args.return_value = self.args_mock
        mock_exists.side_effect = self.existence_router
        mock_path_exists.return_value = True
        mock_open_func.side_effect = self.dynamic_open_router
        
        # 1st call loads configurations, 2nd call throws while loading state mapping file
        mock_json_load.side_effect = [self.valid_combinations, json.JSONDecodeError("State Parse Error", "", 0)]

        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 1)

    # ==========================================
    # DATA LAYER VALIDATION GATES (NO-DEFAULT POLICY)
    # ==========================================

    # The pipeline enforces a strict schema for task details. Missing fields, 
    # malformed structures, or invalid data types (e.g., non-integer orders) 
    # violate the service contract and trigger critical failures.

    @patch("src.pipeline.unified_orchestrator.argparse.ArgumentParser.parse_args")
    @patch("src.pipeline.unified_orchestrator.os.path.exists")
    @patch("pathlib.Path.exists")
    @patch("src.pipeline.unified_orchestrator.open")
    @patch("src.pipeline.unified_orchestrator.json.load")
    def test_state_missing_task_details_key(self, mock_json_load, mock_open_func, mock_path_exists, mock_exists, mock_parse_args):
        """Branch: Key 'task_details' is completely missing inside state.json."""
        mock_parse_args.return_value = self.args_mock
        mock_exists.side_effect = self.existence_router
        mock_path_exists.return_value = True
        mock_open_func.side_effect = self.dynamic_open_router
        
        mock_json_load.side_effect = [self.valid_combinations, {"corrupt_key": []}]

        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 1)

    @patch("src.pipeline.unified_orchestrator.argparse.ArgumentParser.parse_args")
    @patch("src.pipeline.unified_orchestrator.os.path.exists")
    @patch("pathlib.Path.exists")
    @patch("src.pipeline.unified_orchestrator.open")
    @patch("src.pipeline.unified_orchestrator.json.load")
    def test_state_task_details_empty_or_malformed(self, mock_json_load, mock_open_func, mock_path_exists, mock_exists, mock_parse_args):
        """Branch: 'task_details' field is explicitly empty or is not a list structure."""
        mock_parse_args.return_value = self.args_mock
        mock_exists.side_effect = self.existence_router
        mock_path_exists.return_value = True
        mock_open_func.side_effect = self.dynamic_open_router
        
        mock_json_load.side_effect = [self.valid_combinations, {"task_details": []}]

        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 1)

    def run_malformed_task_property_assertion(self, simulated_task_array):
        """Helper to evaluate the no-default validation layer."""
        with patch("src.pipeline.unified_orchestrator.argparse.ArgumentParser.parse_args", return_value=self.args_mock), \
             patch("src.pipeline.unified_orchestrator.os.path.exists", return_value=False), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("src.pipeline.unified_orchestrator.open", side_effect=self.dynamic_open_router), \
             patch("src.pipeline.unified_orchestrator.json.load", side_effect=[self.valid_combinations, {"task_details": simulated_task_array}]):
            
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 1)

    def test_task_item_is_not_a_dictionary_structure(self):
        """Branch: Task config array contains a raw string instead of a valid JSON object."""
        self.run_malformed_task_property_assertion(["corrupt_string_element"])

    def test_task_item_missing_order_parameter(self):
        """Branch: Order field is completely unassigned or missing."""
        task = self.valid_task.copy()
        del task["order"]
        self.run_malformed_task_property_assertion([task])

    def test_task_item_missing_repository_url_parameter(self):
        """Branch: Repository url mapping configuration is missing or blank."""
        task = self.valid_task.copy()
        task["repository_url"] = "   "
        self.run_malformed_task_property_assertion([task])

    def test_task_item_missing_version_tag_parameter(self):
        """Branch: Version deployment tag is missing or blank."""
        task = self.valid_task.copy()
        task["version_tag"] = ""
        self.run_malformed_task_property_assertion([task])

    def test_task_item_missing_input_file_name_parameter(self):
        """Branch: Input context workspace target mapping is blank."""
        task = self.valid_task.copy()
        task["input_file_name"] = " "
        self.run_malformed_task_property_assertion([task])

    def test_task_item_missing_output_file_name_parameter(self):
        """Branch: Output trace asset file target description is blank."""
        task = self.valid_task.copy()
        task["output_file_name"] = ""
        self.run_malformed_task_property_assertion([task])

    @patch("src.pipeline.unified_orchestrator.argparse.ArgumentParser.parse_args")
    @patch("src.pipeline.unified_orchestrator.os.path.exists")
    @patch("pathlib.Path.exists")
    @patch("src.pipeline.unified_orchestrator.open")
    @patch("src.pipeline.unified_orchestrator.json.load")
    def test_task_sorting_by_order_fails(self, mock_json_load, mock_open_func, mock_path_exists, mock_exists, mock_parse_args):
        """Branch: Order parameters cannot be converted to integers, triggering sort exception."""
        mock_parse_args.return_value = self.args_mock
        mock_exists.side_effect = self.existence_router
        mock_path_exists.return_value = True
        mock_open_func.side_effect = self.dynamic_open_router
        
        invalid_sort_task = self.valid_task.copy()
        invalid_sort_task["order"] = "CANNOT_CONVERT_TO_INT"
        
        mock_json_load.side_effect = [self.valid_combinations, {"task_details": [invalid_sort_task]}]

        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 1)

    # ==========================================
    # WORKSPACE RUNTIME PIPELINE EXECUTION LOOP
    # ==========================================

    # The execution loop manages the lifecycle of each task: environment 
    # preparation, repository checkout, and sub-process execution. 
    # It must account for cleanup of stale resources and ensure exit code 
    # propagation in case of sub-process failure.

    @patch("src.pipeline.unified_orchestrator.argparse.ArgumentParser.parse_args")
    @patch("src.pipeline.unified_orchestrator.os.path.exists")
    @patch("src.pipeline.unified_orchestrator.os.remove")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("src.pipeline.unified_orchestrator.open")
    @patch("src.pipeline.unified_orchestrator.json.load")
    @patch("src.pipeline.unified_orchestrator.subprocess.run")
    def test_pipeline_loop_handles_cleanup_and_sub_process_failures(self, mock_sub_run, mock_json_load, mock_open_func, mock_path_mkdir, mock_path_exists, mock_os_remove, mock_exists, mock_parse_args):
        """Branches: Verifies pre-existing trace log deletion, stale repository eviction, and task execution failure paths."""
        mock_parse_args.return_value = self.args_mock
        mock_open_func.side_effect = self.dynamic_open_router
        mock_json_load.side_effect = [self.valid_combinations, self.valid_state]
        
        # Enable cleanup-path testing by simulating existence of workspace artifacts.
        def existence_router(path_obj=None, *args, **kwargs):
            return True
        mock_path_exists.side_effect = existence_router
        mock_exists.side_effect = existence_router
        
        # Mock simulation step execution to report failure.
        mock_failed_result = MagicMock()
        mock_failed_result.returncode = 1
        mock_sub_run.side_effect = [
            MagicMock(returncode=0), # rm -rf stale repo command
            MagicMock(returncode=0), # git clone command
            MagicMock(returncode=0), # git checkout command
            mock_failed_result       # xvfb-run main simulation execution command
        ]

        with self.assertRaises(SystemExit) as cm:
            main()
            
        self.assertEqual(cm.exception.code, 1)
        mock_os_remove.assert_called_once()
        self.assertEqual(mock_sub_run.call_count, 4)

    @patch("src.pipeline.unified_orchestrator.argparse.ArgumentParser.parse_args")
    @patch("src.pipeline.unified_orchestrator.os.path.exists")
    @patch("src.pipeline.unified_orchestrator.os.remove")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("src.pipeline.unified_orchestrator.open")
    @patch("src.pipeline.unified_orchestrator.json.load")
    @patch("src.pipeline.unified_orchestrator.json.loads")
    @patch("src.pipeline.unified_orchestrator.subprocess.run")
    def test_pipeline_loop_complete_nominal_flow(self, mock_sub_run, mock_json_loads, mock_json_load, mock_open_func, mock_path_mkdir, mock_path_exists, mock_os_remove, mock_exists, mock_parse_args):
        # 'Happy Path' validation: Ensure the full chain from resource eviction, 
        # cloning, to execution completes without error.
        mock_parse_args.return_value = self.args_mock
        
        # Explicitly force mock files to retain their string path identity
        def local_open_router(file_path, mode="r", *args, **kwargs):
            mock_file = MagicMock()
            mock_file.name = str(file_path)
            mock_file.__enter__.return_value = mock_file
            return mock_file
            
        mock_open_func.side_effect = local_open_router
        
        # Now guaranteed to match correctly
        def json_load_side_effect(file_obj, *args, **kwargs):
            file_name = str(getattr(file_obj, 'name', ''))
            if "state" in file_name:
                return self.valid_state
            if "combinations" in file_name:
                return self.valid_combinations
            return {}
            
        mock_json_load.side_effect = json_load_side_effect
        mock_json_loads.return_value = {} 
        
        # Safeguard path checking regardless of Path object instantiation
        def existence_router(path_obj=None, *args, **kwargs):
            path_str = str(path_obj)
            return "sim-engine" not in path_str
            
        mock_path_exists.side_effect = existence_router
        mock_exists.side_effect = existence_router
        mock_sub_run.return_value = MagicMock(returncode=0)

        with self.assertRaises(SystemExit) as cm:
            main()
            
        self.assertEqual(cm.exception.code, 0)
        
        # Permissive checking across both shell strings and execution lists
        clone_calls = []
        for call in mock_sub_run.call_args_list:
            cmd_args = call[0][0]
            if isinstance(cmd_args, list) and any("clone" in str(arg) for arg in cmd_args) or isinstance(cmd_args, str) and "clone" in cmd_args:
                clone_calls.append(cmd_args)
                
        self.assertTrue(
            len(clone_calls) > 0, 
            f"Git clone command was bypassed. Captured call signatures: {mock_sub_run.call_args_list}"
        )
        
        # Validate target mapping address updates handled translation layer protocols
        self.assertIn("https://github.com/org/sim-engine.git", str(clone_calls[0]))

    @patch("src.pipeline.unified_orchestrator.argparse.ArgumentParser.parse_args")
    @patch("src.pipeline.unified_orchestrator.os.path.exists")
    @patch("src.pipeline.unified_orchestrator.os.remove")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("src.pipeline.unified_orchestrator.open")
    @patch("src.pipeline.unified_orchestrator.json.load")
    @patch("src.pipeline.unified_orchestrator.json.loads")
    @patch("src.pipeline.unified_orchestrator.subprocess.run")
    def test_matrix_json_parse_error(self, mock_sub_run, mock_json_loads, mock_json_load, mock_open_func, mock_path_mkdir, mock_path_exists, mock_os_remove, mock_exists, mock_parse_args):
        """Triggers Lines 65-68: JSON Decode error handling when matrix configuration is malformed."""
        self.args_mock.state_file = "valid/state.json"
        self.args_mock.log_file = "test.log"
        mock_parse_args.return_value = self.args_mock
        
        # Force all path existence validations to pass cleanly
        mock_path_exists.return_value = True
        mock_exists.return_value = False # Keeps dormant.flag invisible
        
        # Directly force json.load to throw a parsing error when hit
        mock_json_load.side_effect = json.JSONDecodeError("Expecting value", "", 0)
        
        with self.assertRaises(SystemExit) as cm:
            main()
            
        self.assertEqual(cm.exception.code, 1)

    @patch("src.pipeline.unified_orchestrator.argparse.ArgumentParser.parse_args")
    @patch("src.pipeline.unified_orchestrator.os.path.exists")
    @patch("src.pipeline.unified_orchestrator.os.remove")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("src.pipeline.unified_orchestrator.open")
    @patch("src.pipeline.unified_orchestrator.json.load")
    @patch("src.pipeline.unified_orchestrator.json.loads")
    @patch("src.pipeline.unified_orchestrator.subprocess.run")
    def test_matrix_definition_file_missing(self, mock_sub_run, mock_json_loads, mock_json_load, mock_open_func, mock_path_mkdir, mock_path_exists, mock_os_remove, mock_exists, mock_parse_args):
        """Triggers Lines 57-59: Verifies script exits with code 1 if matrix array config is missing."""
        self.args_mock.state_file = "valid/state.json"
        self.args_mock.log_file = "test.log"
        mock_parse_args.return_value = self.args_mock
        
        # Turn off path string inspection entirely to prevent type or index errors.
        # First call (state_path.exists) returns True. Second call (combinations_path.exists) returns False.
        mock_path_exists.side_effect = [True, False, True, True]
        mock_exists.return_value = False # Keeps dormant.flag invisible
        
        with self.assertRaises(SystemExit) as cm:
            main()
            
        self.assertEqual(cm.exception.code, 1)


if __name__ == "__main__":
    unittest.main()