from datetime import datetime, timedelta
from pathlib import Path

import app.backup.retention as retention


def test_parse_timestamped_dirs_filters_and_sorts(tmp_path: Path):
    valid = ["2024-01-01_00-00-00", "2023-12-31_23-59-59"]
    invalid = ["not-a-date", "20240101"]
    for name in valid + invalid:
        path = tmp_path / name
        path.mkdir()
    result = retention.parse_timestamped_dirs(tmp_path)
    assert [p.name for p in result] == sorted(valid, reverse=True)


def test_enforce_retention_respects_rules(tmp_path: Path):
    now = datetime.now()
    backups = []
    for days in range(4):
        stamp = (now - timedelta(days=days)).strftime("%Y-%m-%d_%H-%M-%S")
        folder = tmp_path / stamp
        folder.mkdir()
        backups.append(folder)

    rules = retention.RetentionRules(keep_last=2, max_age_days=1)
    retention.enforce_retention(tmp_path, rules)

    remaining = retention.parse_timestamped_dirs(tmp_path)
    assert len(remaining) <= 2
    assert all((now - datetime.strptime(p.name, "%Y-%m-%d_%H-%M-%S")).days <= 1 for p in remaining)


def test_remove_path_deletes_tree(tmp_path: Path):
    nested = tmp_path / "nested"
    child = nested / "child.txt"
    child.parent.mkdir()
    child.write_text("data")
    retention.remove_path(nested)
    assert not nested.exists()
