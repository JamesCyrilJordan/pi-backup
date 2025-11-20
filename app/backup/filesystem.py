import os
from pathlib import Path
from typing import Iterable, List

from .config import load_config


class UnsafePathError(Exception):
    pass


def is_allowed(path: Path, allowed_roots: Iterable[str]) -> bool:
    resolved = path.resolve()
    for root in allowed_roots:
        try:
            root_path = Path(root).resolve()
            if resolved == root_path or resolved.is_relative_to(root_path):
                return True
        except FileNotFoundError:
            continue
    return False


def list_directory(path: Path) -> List[dict]:
    config = load_config()
    if not is_allowed(path, config.allowed_roots):
        raise UnsafePathError(f"Path {path} is outside allowed roots")

    entries = []
    if path.is_dir():
        for entry in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            entries.append(
                {
                    "name": entry.name,
                    "path": str(entry.resolve()),
                    "is_dir": entry.is_dir(),
                    "size": entry.stat().st_size if entry.is_file() else None,
                }
            )
    return entries


def normalize_selection(selection: List[str]) -> List[str]:
    config = load_config()
    normalized = []
    for item in selection:
        path = Path(item).expanduser()
        if not is_allowed(path, config.allowed_roots):
            continue
        normalized.append(str(path.resolve()))
    return normalized


def ensure_destination(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_relative_to(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path.name


def has_rsync() -> bool:
    from shutil import which

    return which("rsync") is not None
