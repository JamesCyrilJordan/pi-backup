import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from .config import RetentionRules

logger = logging.getLogger(__name__)


def parse_timestamped_dirs(base: Path) -> List[Path]:
    if not base.exists():
        return []
    backups = []
    for entry in base.iterdir():
        if not entry.is_dir():
            continue
        try:
            datetime.strptime(entry.name, "%Y-%m-%d_%H-%M-%S")
            backups.append(entry)
        except ValueError:
            continue
    backups.sort(key=lambda p: p.name, reverse=True)
    return backups


def enforce_retention(base: Path, rules: RetentionRules) -> None:
    backups = parse_timestamped_dirs(base)
    if not backups:
        return

    if rules.keep_last is not None and rules.keep_last >= 0:
        for old in backups[rules.keep_last :]:
            logger.info("Removing old backup %s", old)
            remove_path(old)

    if rules.max_age_days is not None and rules.max_age_days > 0:
        cutoff = datetime.now() - timedelta(days=rules.max_age_days)
        for path in backups:
            try:
                stamp = datetime.strptime(path.name, "%Y-%m-%d_%H-%M-%S")
            except ValueError:
                continue
            if stamp < cutoff:
                logger.info("Removing backup older than %s: %s", cutoff, path)
                remove_path(path)


def remove_path(path: Path) -> None:
    if path.is_dir():
        for child in path.iterdir():
            remove_path(child)
        path.rmdir()
    else:
        path.unlink(missing_ok=True)
