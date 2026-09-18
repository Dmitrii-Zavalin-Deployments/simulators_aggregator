import argparse
import json
import logging
import sys
import zipfile
from pathlib import Path


class ArchiveBuilder:
    """
    Pre-flight packaging and filtering contract for simulation artifacts.
    Enforces full package size ceilings, inner file size limits, and extension criteria strictly from config.
    Raises errors if configuration or required criteria are missing.
    """
    __slots__ = ['config_path', 'logger']

    def __init__(self, config_path: Path = Path("config/config.json")):
        self.config_path = config_path
        self.logger = logging.getLogger(self.__class__.__name__)

    def _load_criteria(self) -> tuple[int, int | None, list[str]]:
        """
        Loads max full size, max inner file size, and allowed extensions from config.json.
        Strictly enforces that all keys must be explicitly defined; raises errors if missing.
        """
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found at {self.config_path}. "
                "No default policy is permitted; explicit configuration is required."
            )

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            
            if not isinstance(config_data, dict):
                raise TypeError("Configuration root must be a JSON object.")

            criteria = config_data.get("upload_criteria")
            if not isinstance(criteria, dict):
                raise KeyError("Missing or invalid 'upload_criteria' dictionary in configuration.")
            
            # Support explicit max_full_size_mb or legacy max_size_mb, without silent defaults
            if "max_full_size_mb" in criteria:
                max_full_mb = criteria["max_full_size_mb"]
            elif "max_size_mb" in criteria:
                max_full_mb = criteria["max_size_mb"]
            else:
                raise KeyError("Missing required configuration key: 'max_full_size_mb' (or legacy 'max_size_mb').")

            if "max_inner_file_size_mb" not in criteria:
                raise KeyError("Missing required configuration key: 'max_inner_file_size_mb'.")

            if "allowed_extensions" not in criteria:
                raise KeyError("Missing required configuration key: 'allowed_extensions'.")

            max_inner_mb = criteria["max_inner_file_size_mb"]
            extensions = criteria["allowed_extensions"]

            if not isinstance(max_full_mb, (int, float)):
                raise TypeError("'max_full_size_mb' must be a numeric value.")
            if max_inner_mb is not None and not isinstance(max_inner_mb, (int, float)):
                raise TypeError("'max_inner_file_size_mb' must be a numeric value or null.")
            if not isinstance(extensions, list):
                raise TypeError("'allowed_extensions' must be a list of strings.")

            inner_bytes = int(max_inner_mb * 1024 * 1024) if max_inner_mb is not None else None
            return int(max_full_mb * 1024 * 1024), inner_bytes, [str(ext).lower() for ext in extensions]

        except (json.JSONDecodeError, OSError) as e:
            if isinstance(e, FileNotFoundError):
                raise
            raise ValueError(f"Failed to parse configuration file {self.config_path}: {e}")

    def inspect_and_build(self, source_dir: Path, output_zip_path: Path) -> Path:
        """
        Inspects staging directory, logs asset sizes, filters by extension and inner file size,
        compiles a compliant zip archive, and validates against the full size ceiling.
        """
        max_full_bytes, max_inner_bytes, allowed_exts = self._load_criteria()

        if not source_dir.exists():
            raise FileNotFoundError(f"Source staging directory not found: {source_dir}")

        self.logger.info(f"🔍 Inspecting staging directory: {source_dir}")
        
        file_records: list[tuple[Path, int]] = []
        total_raw_size = 0

        for item in source_dir.glob("**/*"):
            if item.is_file():
                size = item.stat().st_size
                total_raw_size += size
                file_records.append((item, size))
                self.logger.info(f"   [File] {item.relative_to(source_dir)} ({size / (1024*1024):.2f} MB)")

        self.logger.info(f"📊 Total uncompressed staging size: {total_raw_size / (1024*1024):.2f} MB")

        output_zip_path.parent.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"📦 Compressing compliant files into: {output_zip_path}")
        included_count = 0
        excluded_ext_count = 0
        excluded_size_count = 0

        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path, file_size in file_records:
                rel_path = file_path.relative_to(source_dir)
                ext = file_path.suffix.lower()
                
                # Check extension constraint
                if ext not in allowed_exts:
                    excluded_ext_count += 1
                    self.logger.info(f"   [Skipped - Extension Disallowed] {rel_path}")
                    continue

                # Check inner file size ceiling if defined
                if max_inner_bytes is not None and file_size > max_inner_bytes:
                    excluded_size_count += 1
                    self.logger.warning(
                        f"   [Skipped - Inner File Size Exceeded] {rel_path} "
                        f"({file_size / (1024*1024):.2f} MB > limit {max_inner_bytes / (1024*1024):.2f} MB)"
                    )
                    continue

                zf.write(file_path, rel_path)
                included_count += 1

        final_zip_size = output_zip_path.stat().st_size
        self.logger.info(
            f"✅ Archive built successfully. Included: {included_count}, "
            f"Excluded (Ext): {excluded_ext_count}, Excluded (Inner Size): {excluded_size_count}"
        )
        self.logger.info(f"📦 Final Archive Size: {final_zip_size / (1024*1024):.2f} MB (Full Ceiling: {max_full_bytes / (1024*1024):.2f} MB)")

        if final_zip_size > max_full_bytes:
            output_zip_path.unlink(missing_ok=True)
            raise ValueError(
                f"CRITICAL: Final archive size ({final_zip_size / (1024*1024):.2f} MB) "
                f"exceeds maximum allowed full package ceiling ({max_full_bytes / (1024*1024):.2f} MB)."
            )

        return output_zip_path


def main():
    parser = argparse.ArgumentParser(description="Pre-flight archive builder with strict configuration-driven gating.")
    parser.add_argument("--source", required=True, help="Path to source staging directory")
    parser.add_argument("--output", required=True, help="Path to output zip archive")
    parser.add_argument("--config", default="config/config.json", help="Path to config file")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logger = logging.getLogger("ArchiveBuilder")

    try:
        builder = ArchiveBuilder(config_path=Path(args.config))
        builder.inspect_and_build(Path(args.source), Path(args.output))
    except Exception:
        logger.exception("CRITICAL: Archive packaging failed")
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
