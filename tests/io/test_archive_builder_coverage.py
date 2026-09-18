# tests/io/test_archive_builder_coverage.py
"""
Literate Test Suite: ArchiveBuilder Configuration and Error Boundaries
=====================================================================
Narrative verification ensuring strict configuration validation, 
source directory verification, and clean CLI exception handling under failure modes.
"""

import json

import pytest

from src.io.archive_builder import ArchiveBuilder, main


def test_load_criteria_missing_config(tmp_path):
    """
    Narrative: Under the strict configuration policy, when the configuration file 
    is missing from disk, the builder must not fall back to defaults, but must 
    instead raise a FileNotFoundError.
    """
    # We define a non-existent configuration path to test strict enforcement.
    non_existent_config = tmp_path / "non_existent_config.json"
    builder = ArchiveBuilder(config_path=non_existent_config)

    # Attempting to load criteria from a missing path must raise FileNotFoundError.
    with pytest.raises(FileNotFoundError, match="Configuration file not found"):
        builder._load_criteria()


def test_load_criteria_invalid_json(tmp_path):
    """
    Narrative: When the configuration file contains malformed or corrupt JSON data, 
    the builder must catch the parsing exception and raise a ValueError.
    """
    # We write syntactically invalid text into the configuration file.
    bad_config = tmp_path / "bad_config.json"
    bad_config.write_text("{ invalid json content ...", encoding="utf-8")

    builder = ArchiveBuilder(config_path=bad_config)

    # Attempting to parse malformed JSON must raise a ValueError.
    with pytest.raises(ValueError, match="Failed to parse configuration file"):
        builder._load_criteria()


def test_inspect_and_build_source_not_found(tmp_path):
    """
    Narrative: Pre-flight inspection must enforce strict staging validation; 
    referencing a non-existent source directory must immediately raise a FileNotFoundError.
    """
    # We set up a valid temporary configuration file containing all required criteria keys.
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "upload_criteria": {
            "max_full_size_mb": 100,
            "max_inner_file_size_mb": 10,
            "allowed_extensions": [".txt"]
        }
    }), encoding="utf-8")

    builder = ArchiveBuilder(config_path=config_file)
    non_existent_source = tmp_path / "missing_staging_dir"
    output_zip = tmp_path / "output.zip"

    # Attempting to inspect and build from an absent staging directory must raise FileNotFoundError.
    with pytest.raises(FileNotFoundError, match="Source staging directory not found"):
        builder.inspect_and_build(non_existent_source, output_zip)


def test_main_exception_handling(monkeypatch, tmp_path):
    """
    Narrative: CLI safety boundary verification — any unhandled exception during execution 
    of the main entry point must be trapped by the logger, recorded via logger.exception, 
    and result in a clean termination with status code 1.
    """
    # We mock command-line arguments pointing to a non-existent configuration file to trigger a controlled failure.
    monkeypatch.setattr("sys.argv", [
        "archive_builder.py",
        "--source", str(tmp_path / "staging"),
        "--output", str(tmp_path / "output.zip"),
        "--config", str(tmp_path / "non_existent_config.json")
    ])

    # Execution of the main CLI entry point under these failure conditions must raise SystemExit with exit code 1.
    with pytest.raises(SystemExit) as exc_info:
        main()

    # The expected exit code for critical failure handling is:
    #     exit_code = 1
    assert exc_info.value.code == 1
