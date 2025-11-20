import logging
from pathlib import Path
from typing import List

import pytest

import app.backup.config as config
import app.backup.engine as engine


@pytest.fixture
def source_setup(tmp_path: Path) -> tuple[Path, List[Path]]:
    root = tmp_path / "sources"
    root.mkdir()
    files = []
    for name in ["include.txt", "skip.log", "nested/keep.me"]:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name)
        files.append(path)
    return root, files


def test_configure_logging_is_idempotent(tmp_path: Path):
    log_handler_type = logging.handlers.RotatingFileHandler
    root_logger = logging.getLogger()
    # Remove existing test handlers for isolation.
    root_logger.handlers = [h for h in root_logger.handlers if not isinstance(h, log_handler_type)]

    engine.configure_logging()
    engine.configure_logging()
    count = sum(isinstance(h, log_handler_type) for h in root_logger.handlers)
    assert count == 1


def test_run_backup_requires_sources(tmp_path: Path):
    config.save_config(config.BackupConfig(selected_paths=[], allowed_roots=[str(tmp_path)]))
    with pytest.raises(ValueError):
        engine.run_backup()


def test_run_backup_with_shutil_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source_setup):
    source_root, _ = source_setup
    destination_root = tmp_path / "dest"
    cfg = config.BackupConfig(
        destination=str(destination_root),
        selected_paths=[str(source_root)],
        allowed_roots=[str(tmp_path)],
        include_patterns=["**"],
        exclude_patterns=["*.log"],
    )
    config.save_config(cfg)

    monkeypatch.setattr(engine, "has_rsync", lambda: False)

    destination = engine.run_backup()
    copied_files = list(destination.rglob("*"))
    names = {p.name for p in copied_files if p.is_file()}
    assert "include.txt" in names
    assert "keep.me" in names
    assert "skip.log" not in names


def test_run_backup_with_rsync(monkeypatch: pytest.MonkeyPatch, source_setup, tmp_path: Path):
    source_root, _ = source_setup
    destination_root = tmp_path / "dest"
    cfg = config.BackupConfig(
        destination=str(destination_root),
        selected_paths=[str(source_root)],
        allowed_roots=[str(tmp_path)],
        include_patterns=["*.txt"],
        exclude_patterns=["*.log"],
    )
    config.save_config(cfg)

    monkeypatch.setattr(engine, "has_rsync", lambda: True)
    calls: list[list[str]] = []

    def fake_run(cmd, check):  # type: ignore[override]
        calls.append(cmd)

    monkeypatch.setattr(engine.subprocess, "run", fake_run)

    destination = engine.run_backup()
    assert destination_root.exists()
    assert calls, "rsync should be invoked"
    cmd = calls[0]
    assert "--include" in cmd and "--exclude" in cmd


def test_engine_main_outputs(capsys, monkeypatch: pytest.MonkeyPatch):
    expected_path = Path("/tmp/destination")
    monkeypatch.setattr(engine, "run_backup", lambda: expected_path)
    engine.main()
    captured = capsys.readouterr()
    assert str(expected_path) in captured.out
