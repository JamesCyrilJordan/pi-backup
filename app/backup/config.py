import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_ALLOWED_ROOTS = ["/home/pi", "/mnt", "/media"]
CONFIG_FILENAME = "backup_config.json"


def get_config_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def get_config_path() -> Path:
    return get_config_dir() / CONFIG_FILENAME


@dataclass
class RetentionRules:
    keep_last: Optional[int] = 3
    max_age_days: Optional[int] = None


@dataclass
class BackupConfig:
    destination: str = "/mnt/backups"
    selected_paths: List[str] = field(default_factory=lambda: ["/home/pi/shared"])
    allowed_roots: List[str] = field(default_factory=lambda: DEFAULT_ALLOWED_ROOTS.copy())
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    retention: RetentionRules = field(default_factory=RetentionRules)

    @classmethod
    def from_dict(cls, data: Dict) -> "BackupConfig":
        retention_data = data.get("retention", {})
        retention = RetentionRules(**retention_data) if isinstance(retention_data, dict) else RetentionRules()
        return cls(
            destination=data.get("destination", BackupConfig().destination),
            selected_paths=data.get("selected_paths", []),
            allowed_roots=data.get("allowed_roots", DEFAULT_ALLOWED_ROOTS.copy()),
            include_patterns=data.get("include_patterns", []),
            exclude_patterns=data.get("exclude_patterns", []),
            retention=retention,
        )

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["retention"] = asdict(self.retention)
        return data


def load_config() -> BackupConfig:
    config_path = get_config_path()
    if not config_path.exists():
        return BackupConfig()
    with config_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return BackupConfig.from_dict(data)


def save_config(config: BackupConfig) -> None:
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=2)


def ensure_default_config() -> None:
    config_path = get_config_path()
    if not config_path.exists():
        save_config(BackupConfig())
