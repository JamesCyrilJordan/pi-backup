from pathlib import Path

import pytest

import app.backup.config as config
import app.backup.filesystem as fs


@pytest.fixture
def prepared_root(tmp_path: Path) -> Path:
    root = tmp_path / "allowed"
    root.mkdir()
    config.save_config(config.BackupConfig(allowed_roots=[str(root)], selected_paths=[]))
    return root


def test_is_allowed_with_existing_root(prepared_root: Path):
    assert fs.is_allowed(prepared_root, [str(prepared_root)])
    assert not fs.is_allowed(prepared_root / "outside", [str(prepared_root / "missing")])


def test_list_directory_enforces_allowed_roots(prepared_root: Path):
    (prepared_root / "file.txt").write_text("content")
    entries = fs.list_directory(prepared_root)
    assert entries[0]["name"] == "file.txt"

    with pytest.raises(fs.UnsafePathError):
        fs.list_directory(prepared_root.parent)


def test_normalize_selection_filters_and_expands(prepared_root: Path, monkeypatch: pytest.MonkeyPatch):
    outside = prepared_root.parent / "outside"
    outside.mkdir()
    home_file = prepared_root / "inside.txt"
    home_file.write_text("data")
    selection = [str(home_file), str(outside), "~/nonexistent"]
    normalized = fs.normalize_selection(selection)
    assert str(home_file.resolve()) in normalized
    assert not any(str(outside) in item for item in normalized)


def test_ensure_destination_and_safe_relative_to(tmp_path: Path):
    target = fs.ensure_destination(tmp_path / "dest")
    assert target.exists()

    root = tmp_path / "root"
    root.mkdir()
    nested = root / "child" / "file.txt"
    nested.parent.mkdir(parents=True)
    nested.write_text("data")

    assert fs.safe_relative_to(nested, root) == Path("child/file.txt")
    assert fs.safe_relative_to(nested, tmp_path / "other") == "file.txt"


def test_has_rsync(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/rsync")
    assert fs.has_rsync()
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert not fs.has_rsync()
