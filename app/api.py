import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import JSONResponse

from .backup.config import BackupConfig, load_config, save_config
from .backup.engine import run_backup
from .backup.filesystem import list_directory, normalize_selection, UnsafePathError

api_router = APIRouter()
logger = logging.getLogger(__name__)


@api_router.get("/config", response_model=dict)
def get_config() -> dict:
    config = load_config()
    return config.to_dict()


@api_router.post("/config", response_model=dict)
def update_config(data: dict = Body(...)) -> dict:
    config = BackupConfig.from_dict(data)
    normalized = normalize_selection(config.selected_paths)
    config.selected_paths = normalized
    save_config(config)
    return config.to_dict()


@api_router.get("/browse")
def browse(path: str) -> JSONResponse:
    config = load_config()
    target = Path(path) if path else Path(config.allowed_roots[0])
    try:
        entries = list_directory(target)
    except UnsafePathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse({"path": str(target.resolve()), "entries": entries})


@api_router.post("/run")
def run_backup_now() -> JSONResponse:
    try:
        destination = run_backup()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Backup error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse({"status": "ok", "destination": str(destination)})
