import json
import logging
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .backup.config import BackupConfig, load_config, save_config
from .backup.engine import LOG_FILE, LOG_DIR, run_backup
from .backup.filesystem import list_directory, normalize_selection, UnsafePathError

BASE_PATH = Path(__file__).parent
TEMPLATE_DIR = BASE_PATH / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

view_router = APIRouter()
logger = logging.getLogger(__name__)


@view_router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    config = load_config()
    return templates.TemplateResponse(
        "index.html", {"request": request, "config": config}
    )


@view_router.get("/browse", response_class=HTMLResponse)
async def browse(request: Request, path: str | None = None, error: str | None = None) -> HTMLResponse:
    config = load_config()
    root = Path(path) if path else Path(config.allowed_roots[0])
    try:
        entries = list_directory(root)
        current_path = root.resolve()
    except UnsafePathError as exc:
        entries = []
        current_path = Path(config.allowed_roots[0])
        error = str(exc)
    return templates.TemplateResponse(
        "browse.html",
        {
            "request": request,
            "entries": entries,
            "current_path": str(current_path),
            "config": config,
            "error": error,
        },
    )


@view_router.post("/browse", response_class=HTMLResponse)
async def save_selection(request: Request, selections: str = Form(default="")) -> RedirectResponse:
    config = load_config()
    try:
        selection_list = json.loads(selections) if selections else []
    except json.JSONDecodeError:
        selection_list = []
    normalized = normalize_selection(selection_list)
    config.selected_paths = normalized
    save_config(config)
    return RedirectResponse(url="/", status_code=303)


@view_router.post("/run", response_class=HTMLResponse)
async def run_backup_now() -> RedirectResponse:
    try:
        run_backup()
    except Exception:  # noqa: BLE001
        logger.exception("Backup run failed")
    return RedirectResponse(url="/logs", status_code=303)


@view_router.get("/logs", response_class=HTMLResponse)
async def show_logs(request: Request) -> HTMLResponse:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if LOG_FILE.exists():
        with LOG_FILE.open("r", encoding="utf-8") as f:
            lines = f.readlines()
    else:
        lines = []
    return templates.TemplateResponse(
        "logs.html",
        {"request": request, "logs": reversed(lines[-500:])},
    )
