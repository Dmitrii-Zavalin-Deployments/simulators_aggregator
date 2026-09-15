# tests/io/test_archive_builder_coverage.py
"""
Literate Test Suite: ArchiveBuilder Configuration and Error Boundaries
=====================================================================
Narrative verification ensuring robust configuration fallback behavior, 
source directory validation, and clean CLI exception handling under failure modes.
"""

import json

import pytest

from src.io.archive_builder import ArchiveBuilder, main


def test_load_criteria_missing_config(tmp_path):
    """
    Narrative: When the config file does not exist on disk, the builder must log 
    a warning and gracefully fall back to the default 2GB size limit and standard extensions.
    """
    # We specify a non-existent configuration path to trigger the missing config fallback logic.
    non_existent_config = tmp_path / "non_existent_config.json"
    builder = ArchiveBuilder(config_path=non_existent_config)

    # We load the criteria from the builder instance.
    max_bytes, exts = builder._load_criteria()

    # The fallback size ceiling must equal 2GB in bytes, and default extensions must be present.
    assert max_bytes == 2048 * 1024 * 1024
    assert ".zip" in exts
    assert ".json" in exts


def test_load_criteria_invalid_json(tmp_path):
    """
    Narrative: When the configuration file contains malformed or corrupt JSON data, 
    the builder must catch the parsing error, log an error message, and fall back safely to defaults.
    """
    # We write syntactically invalid text into the configuration file.
    bad_config = tmp_path / "bad_config.json"
    bad_config.write_text("{ invalid json content ...", encoding="utf-8")

    builder = ArchiveBuilder(config_path=bad_config)

    # We invoke criteria loading with the corrupted configuration file in place.
    max_bytes, exts = builder._load_criteria()

    # Default criteria values must be successfully recovered and applied.
    assert max_bytes == 2048 * 1024 * 1024
    assert ".json" in exts


def test_inspect_and_build_source_not_found(tmp_path):
    """
    Narrative: Pre-flight inspection must enforce strict staging validation; 
    referencing a non-existent source directory must immediately raise a FileNotFoundError.
    """
    # We set up a valid temporary configuration file for the builder.
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "upload_criteria": {
            "max_size_mb": 100,
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
    # We mock command-line arguments pointing to a non-existent source directory to trigger a controlled failure.
    monkeypatch.setattr("sys.argv", [
        "archive_builder.py",
        "--source", str(tmp_path / "non_existent_source"),
        "--output", str(tmp_path / "output.zip"),
        "--config", str(tmp_path / "config.json")
    ])

    # Execution of the main CLI entry point under these failure conditions must raise SystemExit with exit code 1.
    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
