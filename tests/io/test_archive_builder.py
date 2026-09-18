# tests/io/test_archive_builder.py
"""
Literate Test Suite: ArchiveBuilder Pre-Flight Gate & Size Ceiling Enforcement
=============================================================================
Narrative verification ensuring compliance with upload criteria, extension filtering,
inner file size limits, and full package size ceiling breach protection before cloud ingress.
"""

import json
from unittest.mock import patch

import pytest

from src.io.archive_builder import ArchiveBuilder, main


def test_archive_builder_filters_and_passes_under_limit(tmp_path):
    """
    Narrative: The ArchiveBuilder must scan a staging directory, log file metrics,
    exclude disallowed file extensions, build a zip archive, and successfully 
    complete when the resulting archive is below the max size ceiling.
    """
    # We establish a strict configuration specifying a 10MB full size limit,
    # no inner file size restriction (null), and allowed extensions ['.h5', '.json'].
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.json"
    config_file.write_text(json.dumps({
        "upload_criteria": {
            "max_full_size_mb": 10,
            "max_inner_file_size_mb": None,
            "allowed_extensions": [".h5", ".json"]
        }
    }))

    # We populate a staging directory with valid and invalid assets.
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    
    valid_file_1 = staging_dir / "sim_output.h5"
    valid_file_1.write_bytes(b"H5_SIMULATION_DATA_STREAM")
    
    valid_file_2 = staging_dir / "metadata.json"
    valid_file_2.write_bytes(b'json_metadata_payload')

    invalid_file = staging_dir / "debug_trace.log"
    invalid_file.write_bytes(b"LARGE_DEBUG_LOG_CONTENT" * 100)

    output_zip = tmp_path / "output" / "simulation_archive.zip"

    # We execute the inspection and archiving workflow.
    builder = ArchiveBuilder(config_path=config_file)
    result_path = builder.inspect_and_build(staging_dir, output_zip)

    # Assertions verify successful build and proper exclusion of disallowed extensions.
    assert result_path.exists()
    assert result_path == output_zip
    
    import zipfile
    with zipfile.ZipFile(result_path, 'r') as zf:
        namelist = zf.namelist()
        assert "sim_output.h5" in namelist
        assert "metadata.json" in namelist
        assert "debug_trace.log" not in namelist


def test_archive_builder_raises_error_on_size_breach(tmp_path):
    """
    Narrative: If the compiled archive exceeds the configured max_full_size_mb ceiling, 
    the ArchiveBuilder must purge the incomplete archive and raise a ValueError.
    """
    # We configure an extremely restrictive ceiling to guarantee a size breach.
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.json"
    config_file.write_text(json.dumps({
        "upload_criteria": {
            "max_full_size_mb": 0.00001,
            "max_inner_file_size_mb": None,
            "allowed_extensions": [".h5"]
        }
    }))

    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    
    heavy_file = staging_dir / "heavy_matrix.h5"
    heavy_file.write_bytes(b"X" * 1024)

    output_zip = tmp_path / "output" / "heavy_archive.zip"

    builder = ArchiveBuilder(config_path=config_file)

    # We assert that a ValueError is raised and the partial archive is cleaned up.
    with pytest.raises(ValueError, match="exceeds maximum allowed full package ceiling"):
        builder.inspect_and_build(staging_dir, output_zip)

    assert not output_zip.exists()


def test_archive_builder_main_cli_execution(tmp_path):
    """
    Narrative: Verify that the CLI entry point main() correctly parses arguments 
    and executes archiving successfully.
    """
    # We set up a valid configuration file for CLI invocation.
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "upload_criteria": {
            "max_full_size_mb": 50,
            "max_inner_file_size_mb": 10,
            "allowed_extensions": [".txt"]
        }
    }))

    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    (staging_dir / "notes.txt").write_text("Hello pipeline")

    output_zip = tmp_path / "archive.zip"

    test_args = [
        "archive_builder.py",
        "--source", str(staging_dir),
        "--output", str(output_zip),
        "--config", str(config_file)
    ]

    # We mock sys.argv to simulate command-line execution and trigger main().
    with patch("sys.argv", test_args):
        main()

    # We confirm the target archive was successfully compiled.
    assert output_zip.exists()
