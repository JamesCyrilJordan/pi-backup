from pathlib import Path

import app.backup.config as config


def test_get_config_path_uses_sandbox(tmp_path: Path):
    config_path = config.get_config_path()
    assert config_path.parent.exists()
    assert config_path.name == config.CONFIG_FILENAME


def test_save_and_load_config_roundtrip(tmp_path: Path):
    custom = config.BackupConfig(
        destination=str(tmp_path / "dest"),
        selected_paths=[str(tmp_path / "data")],
        allowed_roots=[str(tmp_path)],
        include_patterns=["*.txt"],
        exclude_patterns=["*.tmp"],
        retention=config.RetentionRules(keep_last=5, max_age_days=30),
    )
    config.save_config(custom)
    loaded = config.load_config()

    assert loaded.to_dict() == custom.to_dict()


def test_from_dict_handles_missing_retention():
    data = {"destination": "/tmp", "selected_paths": ["/tmp/foo"], "allowed_roots": ["/tmp"]}
    restored = config.BackupConfig.from_dict(data)
    assert restored.retention.keep_last == config.RetentionRules().keep_last


def test_ensure_default_config_creates_file(tmp_path: Path):
    cfg_file = config.get_config_path()
    if cfg_file.exists():
        cfg_file.unlink()

    config.ensure_default_config()
    assert cfg_file.exists()
