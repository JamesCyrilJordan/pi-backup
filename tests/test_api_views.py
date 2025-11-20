from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.backup.config as config
import app.main as main


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    cfg = config.BackupConfig(
        destination=str(tmp_path / "dest"),
        selected_paths=[str(tmp_path / "root")],
        allowed_roots=[str(tmp_path)],
    )
    (tmp_path / "root").mkdir()
    config.save_config(cfg)
    return TestClient(main.app)


def test_api_config_endpoints(client: TestClient, tmp_path: Path):
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["destination"].endswith("dest")

    update_payload = {
        "destination": str(tmp_path / "new"),
        "selected_paths": [str(tmp_path / "root"), str(tmp_path / "forbidden")],
        "allowed_roots": [str(tmp_path)],
    }
    resp = client.post("/api/config", json=update_payload)
    assert resp.status_code == 200
    assert resp.json()["selected_paths"] == [
        str((tmp_path / "root").resolve()),
        str((tmp_path / "forbidden").resolve()),
    ]


def test_api_browse_and_error(client: TestClient, tmp_path: Path):
    target = tmp_path / "root"
    (target / "file.txt").write_text("data")

    resp = client.get(f"/api/browse?path={target}")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["path"] == str(target.resolve())
    assert payload["entries"][0]["name"] == "file.txt"

    resp = client.get("/api/browse?path=/forbidden")
    assert resp.status_code == 400


def test_api_run_backup_success_and_failure(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    destination = Path("/tmp/result")
    monkeypatch.setattr("app.api.run_backup", lambda: destination)
    resp = client.post("/api/run")
    assert resp.status_code == 200
    assert resp.json()["destination"] == str(destination)

    def boom():
        raise RuntimeError("fail")

    monkeypatch.setattr("app.api.run_backup", boom)
    resp = client.post("/api/run")
    assert resp.status_code == 500


def test_views_flow(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Index renders config
    resp = client.get("/")
    assert resp.status_code == 200

    # Browse with invalid path
    resp = client.get("/browse?path=/invalid")
    assert resp.status_code == 200

    # Save selection with malformed JSON falls back to empty
    resp = client.post("/browse", data={"selections": "not-json"}, allow_redirects=False)
    assert resp.status_code == 303

    # Run backup captures errors and redirects
    monkeypatch.setattr("app.views.run_backup", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    resp = client.post("/run", allow_redirects=False)
    assert resp.status_code == 303

    # Logs page reads existing file
    from app.backup import engine

    log_file = Path(engine.LOG_FILE)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text("line1\nline2\n")
    resp = client.get("/logs")
    assert resp.status_code == 200
    assert "line1" in resp.text
