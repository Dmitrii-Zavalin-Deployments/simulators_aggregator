import argparse
import json
import logging
import sys
import zipfile
from pathlib import Path
from typing import List, Tuple


class ArchiveBuilder:
    """
    Pre-flight packaging and filtering contract for simulation artifacts.
    Enforces size ceilings and extension criteria from config before cloud ingress.
    """
    __slots__ = ['config_path', 'logger']

    def __init__(self, config_path: Path = Path("config/config.json")):
        self.config_path = config_path
        self.logger = logging.getLogger(self.__class__.__name__)

    def _load_criteria(self) -> Tuple[int, List[str]]:
        """Loads max size in bytes and allowed extensions from config.json."""
        if not self.config_path.exists():
            self.logger.warning(f"Config not found at {self.config_path}. Using default 2GB limit.")
            return 2048 * 1024 * 1024, [".h5", ".json", ".yaml", ".csv", ".txt", ".zip"]

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            criteria = config_data.get("upload_criteria", {})
            max_size_mb = criteria.get("max_size_mb", 2048)
            extensions = criteria.get("allowed_extensions", [".h5", ".json", ".yaml", ".csv", ".txt"])
            return max_size_mb * 1024 * 1024, [ext.lower() for ext in extensions]
        except (json.JSONDecodeError, KeyError, TypeError, OSError) as e:
            self.logger.error(f"Failed to parse config criteria: {e}. Falling back to defaults.")
            return 2048 * 1024 * 1024, [".h5", ".json", ".yaml", ".csv", ".txt"]

    def inspect_and_build(self, source_dir: Path, output_zip_path: Path) -> Path:
        """
        Inspects staging directory, logs asset sizes, filters by extension,
        compiles a compliant zip archive, and validates against the size ceiling.
        """
        max_bytes, allowed_exts = self._load_criteria()

        if not source_dir.exists():
            raise FileNotFoundError(f"Source staging directory not found: {source_dir}")

        self.logger.info(f"🔍 Inspecting staging directory: {source_dir}")
        
        file_records: List[Tuple[Path, int]] = []
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
        excluded_count = 0

        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path, file_size in file_records:
                ext = file_path.suffix.lower()
                if ext in allowed_exts:
                    arcname = file_path.relative_to(source_dir)
                    zf.write(file_path, arcname)
                    included_count += 1
                else:
                    excluded_count += 1
                    self.logger.info(f"   [Skipped - Extension Disallowed] {file_path.relative_to(source_dir)}")

        final_zip_size = output_zip_path.stat().st_size
        self.logger.info(f"✅ Archive built successfully. Included: {included_count}, Excluded: {excluded_count}")
        self.logger.info(f"📦 Final Archive Size: {final_zip_size / (1024*1024):.2f} MB (Ceiling: {max_bytes / (1024*1024):.2f} MB)")

        if final_zip_size > max_bytes:
            output_zip_path.unlink(missing_ok=True)
            raise ValueError(
                f"CRITICAL: Final archive size ({final_zip_size / (1024*1024):.2f} MB) "
                f"exceeds maximum allowed Dropbox ceiling ({max_bytes / (1024*1024):.2f} MB)."
            )

        return output_zip_path


def main():
    parser = argparse.ArgumentParser(description="Pre-flight archive builder with size and extension gating.")
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
