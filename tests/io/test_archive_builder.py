# tests/io/test_archive_builder.py
"""
Literate Test Suite: ArchiveBuilder Pre-Flight Gate & Size Ceiling Enforcement
=============================================================================
Narrative verification ensuring compliance with upload criteria, extension filtering,
and hard 2GB ceiling breach protection before cloud ingress.
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
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.json"
    config_file.write_text(json.dumps({
        "upload_criteria": {
            "max_size_mb": 10,
            "allowed_extensions": [".h5", ".json"]
        }
    }))

    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    
    valid_file_1 = staging_dir / "sim_output.h5"
    valid_file_1.write_bytes(b"H5_SIMULATION_DATA_STREAM")
    
    valid_file_2 = staging_dir / "metadata.json"
    valid_file_2.write_bytes(b'{"status": "complete"}')

    invalid_file = staging_dir / "debug_trace.log"
    invalid_file.write_bytes(b"LARGE_DEBUG_LOG_CONTENT" * 100)

    output_zip = tmp_path / "output" / "simulation_archive.zip"

    builder = ArchiveBuilder(config_path=config_file)
    result_path = builder.inspect_and_build(staging_dir, output_zip)

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
    Narrative: If the compiled archive exceeds the configured max_size_mb ceiling, 
    the ArchiveBuilder must purge the incomplete archive and raise a ValueError.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.json"
    config_file.write_text(json.dumps({
        "upload_criteria": {
            "max_size_mb": 0.00001,
            "allowed_extensions": [".h5"]
        }
    }))

    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    
    heavy_file = staging_dir / "heavy_matrix.h5"
    heavy_file.write_bytes(b"X" * 1024)

    output_zip = tmp_path / "output" / "heavy_archive.zip"

    builder = ArchiveBuilder(config_path=config_file)

    with pytest.raises(ValueError, match="exceeds maximum allowed Dropbox ceiling"):
        builder.inspect_and_build(staging_dir, output_zip)

    assert not output_zip.exists()


def test_archive_builder_main_cli_execution(tmp_path):
    """
    Narrative: Verify that the CLI entry point main() correctly parses arguments 
    and executes archiving successfully.
    """
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "upload_criteria": {
            "max_size_mb": 50,
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

    with patch("sys.argv", test_args):
        main()

    assert output_zip.exists()
