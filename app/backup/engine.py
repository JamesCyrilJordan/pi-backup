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
    def is_included(relative_path: Path) -> bool:
        rel_str = relative_path.as_posix().lstrip("./")
        include_match = next((pattern for pattern in include_patterns if fnmatch.fnmatch(rel_str, pattern)), None)
        if include_match:
            logger.debug("Including %s because it matches include pattern %s", rel_str, include_match)
            return True

        excluded_match = next((pattern for pattern in exclude_patterns if fnmatch.fnmatch(rel_str, pattern)), None)
        if excluded_match:
            logger.debug("Skipping %s because it matches exclude pattern %s", rel_str, excluded_match)
            return False

        if include_patterns:
            logger.debug("Skipping %s because it does not match any include pattern", rel_str)
            return False

        return True

    def should_descend(relative_dir: Path) -> bool:
        rel_str = relative_dir.as_posix().lstrip("./")
        if rel_str == "":
            return True

        def has_potential_include() -> bool:
            if not include_patterns:
                return True
            for pattern in include_patterns:
                if "/" not in pattern:
                    return True
                if fnmatch.fnmatch(rel_str, pattern) or pattern.startswith(f"{rel_str}/"):
                    return True
            return False

        potential_include = has_potential_include()
        excluded_match = next((pattern for pattern in exclude_patterns if fnmatch.fnmatch(rel_str, pattern)), None)

        if not include_patterns and excluded_match:
            logger.debug("Pruning directory %s because it matches exclude pattern %s", rel_str, excluded_match)
            return False

        if not potential_include:
            logger.debug("Pruning directory %s because it is not covered by include patterns", rel_str)
            return False

        if excluded_match and potential_include:
            logger.debug(
                "Retaining directory %s despite exclude pattern %s because it matches include patterns",
                rel_str,
                excluded_match,
            )

        return True

    for src in sources:
        src_path = Path(src)
        dest_path = destination / src_path.name
        if src_path.is_dir():
            for root, dirs, files in os.walk(src_path):
                rel_root = Path(root).relative_to(src_path)
                if rel_root == Path("."):
                    rel_root = Path()
                dirs[:] = [
                    d
                    for d in dirs
                    if should_descend(rel_root / d)
                ]

                for file in files:
                    rel_file = rel_root / file
                    if not is_included(rel_file):
                        continue
                    src_file = Path(root) / file
                    dest_file = dest_path / rel_file
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dest_file)
        elif src_path.is_file():
            if not is_included(Path(src_path.name)):
                continue
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
