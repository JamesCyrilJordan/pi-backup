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
    for src in sources:
        src_path = Path(src)
        dest_path = destination / src_path.name
        if src_path.is_dir():
            shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
        elif src_path.is_file():
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
