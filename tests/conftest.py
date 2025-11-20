import importlib
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def reload_modules(config_dir: Path, log_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Reload and patch configuration so all modules point to the temporary directory.
    import app.backup.config as config

    importlib.reload(config)
    monkeypatch.setattr(config, "get_config_dir", lambda: config_dir)

    # Reload dependent modules to pick up the patched configuration.
    import app.backup.filesystem as filesystem
    import app.backup.retention as retention
    import app.backup.engine as engine

    importlib.reload(filesystem)
    importlib.reload(retention)
    engine = importlib.reload(engine)

    # Ensure logs are written inside the test sandbox.
    monkeypatch.setattr(engine, "LOG_DIR", log_dir)
    monkeypatch.setattr(engine, "LOG_FILE", log_dir / "backup.log")

    # Reload FastAPI layers so they import the patched engine/config values.
    import app.api as api
    import app.views as views
    import app.main as main

    importlib.reload(api)
    importlib.reload(views)
    importlib.reload(main)


@pytest.fixture(autouse=True)
def sandbox(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    config_dir = tmp_path / "config"
    log_dir = tmp_path / "logs"
    config_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    reload_modules(config_dir, log_dir, monkeypatch)
    yield
