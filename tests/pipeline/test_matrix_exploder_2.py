import unittest
import json
from unittest.mock import patch, MagicMock, mock_open

# Import functions from your module
from src.pipeline.matrix_exploder import explode_dict, main


class TestMatrixExploder(unittest.TestCase):

    # ==========================================
    # UNIT TESTS: explode_dict()
    # ==========================================

    def test_explode_dict_non_dict(self):
        """Branch: target_dict is not an instance of dict."""
        input_data = [1, 2, 3]
        result = explode_dict(input_data)
        self.assertEqual(result, [[1, 2, 3]])

    def test_explode_dict_scalars_and_lists(self):
        """Branches: handles list types and scalar fallbacks."""
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
        """Branch: dict value inside target_dict triggers recursive call."""
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

    @patch("src.pipeline.matrix_exploder.argparse.ArgumentParser.parse_args")
    @patch("src.pipeline.matrix_exploder.os.path.exists")
    def test_main_config_file_not_found(self, mock_exists, mock_parse_args):
        """Branch: Configuration file does not exist, triggers sys.exit(1)."""
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
        """Branch: JSON parsing fails, raises JSONDecodeError, triggers sys.exit(1)."""
        mock_parse_args.return_value = MagicMock(
            config_path="bad_config.json", 
            output_path="output/results.json"
        )
        mock_exists.return_value = True
        
        # Simulate a real JSONDecodeError exception
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
        """Branches: Exhaustive integration test hitting all loop variations in main()."""
        mock_parse_args.return_value = MagicMock(
            config_path="valid_config.json", 
            output_path="output/results.json"
        )
        mock_exists.return_value = True
        
        # Comprehensive mock config payload hitting every conditional item route inside main()
        mock_json_load.return_value = {
            "boundary_map": {"resolution": [1, 2]},  # Hits key=="boundary_map" and dict check
            "arrays": [10, 20],                       # Hits isinstance(v, list) check
            "constant": "static_string"               # Hits scalar fallback else check
        }

        main()

        # Verify output directory structural preparations happened
        mock_makedirs.assert_called_once_with("output", exist_ok=True)
        
        # Verify JSON permutations calculation payload was safely written out
        mock_json_dump.assert_called_once()
        
        # Pull out what was written via JSON dump to assert correctness
        generated_combinations = mock_json_dump.call_args[0][0]
        self.assertEqual(len(generated_combinations), 4)


if __name__ == "__main__":
    unittest.main()