import fnmatch
import logging
import os
import shutil
import subprocess
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List

from .config import BackupConfig, load_config
from .filesystem import ensure_destination, has_rsync, normalize_selection
from .retention import enforce_retention

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "backup.log"

logger = logging.getLogger("backup")


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(LOG_FILE, maxBytes=512000, backupCount=3)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    root = logging.getLogger()
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        root.setLevel(logging.INFO)
        root.addHandler(handler)


def _copy_with_shutil(sources: List[str], destination: Path, include_patterns: List[str], exclude_patterns: List[str]) -> None:
    def should_include(path: Path) -> bool:
        path_str = str(path)
        if any(fnmatch.fnmatch(path_str, pattern) for pattern in exclude_patterns):
            return False
        if include_patterns:
            return any(fnmatch.fnmatch(path_str, pattern) for pattern in include_patterns)
        return True

    for src in sources:
        src_path = Path(src)
        dest_path = destination / src_path.name
        if src_path.is_dir():
            for root, dirs, files in os.walk(src_path):
                root_path = Path(root)
                rel_root = root_path.relative_to(src_path)

                dirs[:] = [d for d in dirs if should_include(rel_root / d)]

                for file_name in files:
                    rel_file = rel_root / file_name
                    if not should_include(rel_file):
                        continue
                    source_file = root_path / file_name
                    target_file = dest_path / rel_file
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_file, target_file)
        elif src_path.is_file():
            if should_include(Path(src_path.name)):
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dest_path)
        else:
            logger.warning("Skipping unknown path %s", src_path)


def _run_rsync(sources: List[str], destination: Path, include_patterns: List[str], exclude_patterns: List[str]) -> None:
    base_cmd = [
        "rsync",
        "-a",
        "--delete",
    ]
    for pattern in include_patterns:
        base_cmd.extend(["--include", pattern])
    for pattern in exclude_patterns:
        base_cmd.extend(["--exclude", pattern])
    base_cmd.append("--info=progress2")

    for src in sources:
        cmd = base_cmd + [src, str(destination)]
        logger.info("Running rsync: %s", " ".join(cmd))
        subprocess.run(cmd, check=True)


def run_backup(config: BackupConfig | None = None) -> Path:
    config = config or load_config()
    sources = normalize_selection(config.selected_paths)
    if not sources:
        raise ValueError("No sources selected for backup")

    destination_root = ensure_destination(Path(config.destination))
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    destination = destination_root / timestamp
    destination.mkdir(parents=True, exist_ok=True)

    logger.info("Starting backup to %s", destination)

    try:
        if has_rsync():
            _run_rsync(sources, destination, config.include_patterns, config.exclude_patterns)
        else:
            _copy_with_shutil(sources, destination, config.include_patterns, config.exclude_patterns)
        logger.info("Backup completed successfully")
    except subprocess.CalledProcessError as exc:
        logger.exception("Backup failed: %s", exc)
        raise

    enforce_retention(destination_root, config.retention)
    return destination


def main() -> None:
    destination = run_backup()
    print(f"Backup complete: {destination}")


if __name__ == "__main__":
    configure_logging()
    main()
