import unittest
import json
from unittest.mock import patch, MagicMock, mock_open

# Import functions from your module
from src.pipeline.matrix_exploder import explode_dict, main

class TestMatrixExploder(unittest.TestCase):

    # ==========================================
    # UNIT TESTS: explode_dict()
    # ==========================================

    # The `explode_dict` function acts as the combinatorial engine. 
    # It must handle various input types—scalars, lists, and nested objects—
    # transforming them into a flat Cartesian product list.

    def test_explode_dict_non_dict(self):
        # We verify the base case: if the input is not a dictionary, it cannot be 
        # exploded recursively. The function must treat it as an atomic unit 
        # and wrap it in a list to maintain compatibility with the result schema.
        input_data = [1, 2, 3]
        result = explode_dict(input_data)
        self.assertEqual(result, [[1, 2, 3]])

    def test_explode_dict_scalars_and_lists(self):
        # We test the primary transformation logic. Scalars act as constant anchors,
        # while lists act as branching variables. 
        # Expected: A product of 1 (scalar) * 2 (list) = 2 total permutations.
        input_dict = {
            "scalar_val": 42,
            "list_val": [1, 2]
        }
        expected = [
            {"scalar_val": 42, "list_val": 1},
            {"scalar_val": 42, "list_val": 2}
        ]
        self.assertEqual(explode_dict(input_dict), expected)

    def test_explode_dict_recursive_nested_dict(self):
        # We verify recursive depth. If a dictionary value contains its own 
        # internal lists, the function must dive into the nested structure 
        # to ensure global permutation coverage.
        input_dict = {
            "nested": {
                "deep_list": [10, 20]
            }
        }
        expected = [
            {"nested": {"deep_list": 10}},
            {"nested": {"deep_list": 20}}
        ]
        self.assertEqual(explode_dict(input_dict), expected)

    # ==========================================
    # UNIT TESTS: main() Pipeline Flow
    # ==========================================

    # The `main` pipeline entry point manages the CLI orchestration,
    # filesystem preparation, and error handling. It must guarantee that 
    # system failures result in controlled termination.

    @patch("src.pipeline.matrix_exploder.argparse.ArgumentParser.parse_args")
    @patch("src.pipeline.matrix_exploder.os.path.exists")
    def test_main_config_file_not_found(self, mock_exists, mock_parse_args):
        # The system must enforce existence of the input manifest. 
        # If the file path provided via CLI is invalid, we trigger a SystemExit(1)
        # to prevent downstream execution on missing state.
        mock_parse_args.return_value = MagicMock(
            config_path="missing_config.json", 
            output_path="output/results.json"
        )
        mock_exists.return_value = False

        with self.assertRaises(SystemExit) as cm:
            main()
        
        self.assertEqual(cm.exception.code, 1)

    @patch("src.pipeline.matrix_exploder.argparse.ArgumentParser.parse_args")
    @patch("src.pipeline.matrix_exploder.os.path.exists")
    @patch("src.pipeline.matrix_exploder.open", new_callable=lambda: mock_open(read_data=b"{}"))
    @patch("src.pipeline.matrix_exploder.json.load")
    def test_main_invalid_json_decode_error(self, mock_json_load, mock_file_open, mock_exists, mock_parse_args):
        # Data integrity is paramount. If the configuration manifest is corrupted
        # (invalid JSON), the pipeline must detect the decoding failure,
        # log the issue, and halt execution to avoid generating invalid permutations.
        mock_parse_args.return_value = MagicMock(
            config_path="bad_config.json", 
            output_path="output/results.json"
        )
        mock_exists.return_value = True
        
        # We inject a JSONDecodeError to simulate corrupted configuration data.
        mock_json_load.side_effect = json.JSONDecodeError("Expecting value", "", 0)

        with self.assertRaises(SystemExit) as cm:
            main()
            
        self.assertEqual(cm.exception.code, 1)

    @patch("src.pipeline.matrix_exploder.argparse.ArgumentParser.parse_args")
    @patch("src.pipeline.matrix_exploder.os.path.exists")
    @patch("src.pipeline.matrix_exploder.open", new_callable=lambda: mock_open(read_data=b"{}"))
    @patch("src.pipeline.matrix_exploder.json.load")
    @patch("src.pipeline.matrix_exploder.os.makedirs")
    @patch("src.pipeline.matrix_exploder.json.dump")
    def test_main_success_flow(self, mock_json_dump, mock_makedirs, mock_json_load, mock_file_open, mock_exists, mock_parse_args):
        # We validate the end-to-end "Happy Path." 
        # 1. Parse valid CLI arguments.
        # 2. Prepare the output directory.
        # 3. Perform the Cartesian expansion.
        # 4. Serialize the resulting configuration matrix to disk.
        mock_parse_args.return_value = MagicMock(
            config_path="valid_config.json", 
            output_path="output/results.json"
        )
        mock_exists.return_value = True
        
        # We define a payload that hits every branching conditional in the main logic:
        # - Dictionary nested structures ('boundary_map')
        # - List types for permutation ('arrays')
        # - Scalar fallbacks ('constant')
        mock_json_load.return_value = {
            "boundary_map": {"resolution": [1, 2]},  
            "arrays": [10, 20],                      
            "constant": "static_string"              
        }

        main()

        # We verify that the directory structure was prepared correctly.
        mock_makedirs.assert_called_once_with("output", exist_ok=True)
        
        # We verify the data dump, ensuring the permutation count matches 
        # the mathematical expectation (2 * 2 = 4 combinations).
        mock_json_dump.assert_called_once()
        generated_combinations = mock_json_dump.call_args[0][0]
        self.assertEqual(len(generated_combinations), 4)

if __name__ == "__main__":
    unittest.main()