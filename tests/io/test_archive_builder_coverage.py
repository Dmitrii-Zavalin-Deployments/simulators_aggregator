# tests/io/test_archive_builder_coverage.py
"""
Literate Test Suite: ArchiveBuilder 100% Coverage & Error Boundary Enforcement
=============================================================================
Narrative verification ensuring complete code path coverage for configuration validation,
type checking, exception re-raising, and inner file size exclusion logic.
"""

import json
from pathlib import Path
from unittest.mock import patch
import pytest

from src.io.archive_builder import ArchiveBuilder, main


def test_config_root_not_object(tmp_path):
    """
    Narrative: When the configuration file root is a JSON array rather than an object,
    the builder must raise a TypeError.
    """
    # We write a JSON list instead of an object to the configuration file.
    bad_config = tmp_path / "config.json"
    bad_config.write_text("[]", encoding="utf-8")

    builder = ArchiveBuilder(config_path=bad_config)

    # Parsing a non-object root must trigger TypeError.
    with pytest.raises(TypeError, match="Configuration root must be a JSON object"):
        builder._load_criteria()


def test_upload_criteria_missing_or_invalid(tmp_path):
    """
    Narrative: When the 'upload_criteria' key is missing or not a dictionary,
    the builder must raise a KeyError.
    """
    # We supply a dictionary without 'upload_criteria'.
    bad_config = tmp_path / "config.json"
    bad_config.write_text(json.dumps({"wrong_key": {}}), encoding="utf-8")

    builder = ArchiveBuilder(config_path=bad_config)

    # Missing upload_criteria must raise KeyError.
    with pytest.raises(KeyError, match="Missing or invalid 'upload_criteria'"):
        builder._load_criteria()


def test_legacy_max_size_mb_support(tmp_path):
    """
    Narrative: The builder must support legacy 'max_size_mb' key as a fallback
    when 'max_full_size_mb' is absent from upload_criteria.
    """
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "upload_criteria": {
            "max_size_mb": 500,
            "max_inner_file_size_mb": 50,
            "allowed_extensions": [".txt"]
        }
    }), encoding="utf-8")

    builder = ArchiveBuilder(config_path=config_file)
    max_bytes, _, _ = builder._load_criteria()

    # The legacy 500 MB limit must convert correctly to bytes:
    #     expected_bytes = 500 * 1024 * 1024 = 524288000
    assert max_bytes == 500 * 1024 * 1024


def test_missing_max_full_size_keys(tmp_path):
    """
    Narrative: When neither 'max_full_size_mb' nor legacy 'max_size_mb' is provided,
    the builder must raise a KeyError.
    """
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "upload_criteria": {
            "max_inner_file_size_mb": 50,
            "allowed_extensions": [".txt"]
        }
    }), encoding="utf-8")

    builder = ArchiveBuilder(config_path=config_file)
    with pytest.raises(KeyError, match="Missing required configuration key: 'max_full_size_mb'"):
        builder._load_criteria()


def test_missing_max_inner_file_size_key(tmp_path):
    """
    Narrative: When 'max_inner_file_size_mb' is missing from upload_criteria,
    the builder must raise a KeyError.
    """
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "upload_criteria": {
            "max_full_size_mb": 100,
            "allowed_extensions": [".txt"]
        }
    }), encoding="utf-8")

    builder = ArchiveBuilder(config_path=config_file)
    with pytest.raises(KeyError, match="Missing required configuration key: 'max_inner_file_size_mb'"):
        builder._load_criteria()


def test_missing_allowed_extensions_key(tmp_path):
    """
    Narrative: When 'allowed_extensions' is missing from upload_criteria,
    the builder must raise a KeyError.
    """
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "upload_criteria": {
            "max_full_size_mb": 100,
            "max_inner_file_size_mb": 10
        }
    }), encoding="utf-8")

    builder = ArchiveBuilder(config_path=config_file)
    with pytest.raises(KeyError, match="Missing required configuration key: 'allowed_extensions'"):
        builder._load_criteria()


def test_invalid_type_max_full_size(tmp_path):
    """
    Narrative: When 'max_full_size_mb' is not a numeric value, a TypeError is raised.
    """
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "upload_criteria": {
            "max_full_size_mb": "not-a-number",
            "max_inner_file_size_mb": 10,
            "allowed_extensions": [".txt"]
        }
    }), encoding="utf-8")

    builder = ArchiveBuilder(config_path=config_file)
    with pytest.raises(TypeError, match="'max_full_size_mb' must be a numeric value"):
        builder._load_criteria()


def test_invalid_type_max_inner_file_size(tmp_path):
    """
    Narrative: When 'max_inner_file_size_mb' is neither numeric nor null, a TypeError is raised.
    """
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "upload_criteria": {
            "max_full_size_mb": 100,
            "max_inner_file_size_mb": "invalid-type",
            "allowed_extensions": [".txt"]
        }
    }), encoding="utf-8")

    builder = ArchiveBuilder(config_path=config_file)
    with pytest.raises(TypeError, match="'max_inner_file_size_mb' must be a numeric value or null"):
        builder._load_criteria()


def test_invalid_type_allowed_extensions(tmp_path):
    """
    Narrative: When 'allowed_extensions' is not a list, a TypeError is raised.
    """
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "upload_criteria": {
            "max_full_size_mb": 100,
            "max_inner_file_size_mb": 10,
            "allowed_extensions": ".txt"
        }
    }), encoding="utf-8")

    builder = ArchiveBuilder(config_path=config_file)
    with pytest.raises(TypeError, match="'allowed_extensions' must be a list of strings"):
        builder._load_criteria()


def test_file_not_found_reraise(tmp_path):
    """
    Narrative: When FileNotFoundError occurs during file operations inside the try-except block,
    it must be caught and re-raised directly without being wrapped in ValueError.
    """
    config_file = tmp_path / "config.json"
    config_file.write_text("{}", encoding="utf-8")

    builder = ArchiveBuilder(config_path=config_file)

    # We mock Path.exists to return True so it passes pre-flight existence checks,
    # but open() raises FileNotFoundError.
    with patch.object(Path, "exists", return_value=True), \
         patch("builtins.open", side_effect=FileNotFoundError("Config file vanished")):
        with pytest.raises(FileNotFoundError, match="Config file vanished"):
            builder._load_criteria()


def test_inner_file_size_exceeded_exclusion(tmp_path):
    """
    Narrative: When an individual file exceeds the 'max_inner_file_size_mb' limit,
    it must be excluded from the archive and trigger the warning and continue flow.
    """
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "upload_criteria": {
            "max_full_size_mb": 100,
            "max_inner_file_size_mb": 0.000001,  # extremely small limit (~1 byte)
            "allowed_extensions": [".txt"]
        }
    }), encoding="utf-8")

    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    
    oversized_file = staging_dir / "large.txt"
    oversized_file.write_bytes(b"A" * 1024)  # 1 KB > 1 byte limit

    output_zip = tmp_path / "output.zip"

    builder = ArchiveBuilder(config_path=config_file)
    result_path = builder.inspect_and_build(staging_dir, output_zip)

    assert result_path.exists()
    
    import zipfile
    with zipfile.ZipFile(result_path, 'r') as zf:
        # The oversized file should be excluded
        assert "large.txt" not in zf.namelist()


def test_load_criteria_missing_config(tmp_path):
    non_existent = tmp_path / "non_existent_config.json"
    builder = ArchiveBuilder(config_path=non_existent)
    with pytest.raises(FileNotFoundError):
        builder._load_criteria()


def test_load_criteria_invalid_json(tmp_path):
    bad_config = tmp_path / "bad_config.json"
    bad_config.write_text("{ invalid json")
    builder = ArchiveBuilder(config_path=bad_config)
    with pytest.raises(ValueError, match="Failed to parse configuration file"):
        builder._load_criteria()


def test_inspect_and_build_source_not_found(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "upload_criteria": {
            "max_full_size_mb": 10,
            "max_inner_file_size_mb": 5,
            "allowed_extensions": [".json"]
        }
    }))
    builder = ArchiveBuilder(config_path=config_file)
    non_existent_dir = tmp_path / "ghost_dir"
    with pytest.raises(FileNotFoundError, match="Source staging directory not found"):
        builder.inspect_and_build(non_existent_dir, tmp_path / "out.zip")


def test_main_cli_exception_handling(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "archive_builder.py",
            "--source", str(tmp_path / "non_existent"),
            "--output", str(tmp_path / "out.zip"),
            "--config", str(tmp_path / "non_existent_config.json"),
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1