import json
import os
import tempfile
import unittest
from unittest.mock import patch

from src.pipeline.matrix_exploder import explode_dict, explode_value, main


class TestMatrixExploder(unittest.TestCase):

    def test_explode_dict_non_dict(self):
        input_data = [1, 2, 3]
        result = explode_dict(input_data)
        self.assertEqual(result, [[1, 2, 3]])

    def test_explode_dict_recursive_nested_dict(self):
        data = {"a": {"b": [1, 2]}}
        result = explode_dict(data)
        self.assertEqual(result, [{"a": {"b": 1}}, {"a": {"b": 2}}])

    def test_explode_dict_scalars_and_lists(self):
        data = {"a": [1, 2]}
        result = explode_dict(data)
        self.assertEqual(result, [{"a": 1}, {"a": 2}])

    def test_explode_value_empty_list(self):
        # Covers line 28: empty list expansion returning [[]]
        result = explode_value([])
        self.assertEqual(result, [[]])

    def test_explode_value_list_of_dicts_or_lists(self):
        # Covers lines 30-34: list containing dictionaries or nested structures
        input_list = [{"x": [1, 2]}]
        result = explode_value(input_list)
        self.assertEqual(result, [[{"x": 1}], [{"x": 2}]])

    def test_main_config_file_not_found(self):
        with patch("sys.argv", ["matrix_exploder.py", "--config-path", "non_existent_config_9999.json", "--output-path", "out.json"]):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 1)

    def test_main_invalid_json_decode_error(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tf:
            tf.write("{ invalid json }")
            tf_name = tf.name
        try:
            with patch("sys.argv", ["matrix_exploder.py", "--config-path", tf_name, "--output-path", "out.json"]):
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 1)
        finally:
            if os.path.exists(tf_name):
                os.unlink(tf_name)

    def test_main_success_flow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            output_path = os.path.join(tmpdir, "output.json")
            
            with open(config_path, "w") as f:
                json.dump({"param": [1, 2]}, f)

            with patch("sys.argv", ["matrix_exploder.py", "--config-path", config_path, "--output-path", output_path]):
                main()

            self.assertTrue(os.path.exists(output_path))
            with open(output_path, "r") as f:
                data = json.load(f)
            self.assertEqual(data, [{"param": 1}, {"param": 2}])
